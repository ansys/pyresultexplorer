# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import warnings
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

import grpc
from ansys.api.result_explorer.v0 import (
    app_pb2_grpc,
    filesystem_pb2_grpc,
    solution_pb2_grpc,
    workspace_pb2_grpc,
)

from ansys.result_explorer.core import models

from .exceptions import ResultExplorerError, UnsecureConnectionWarning
from .objects import Solution, Viewport, Workspace

if TYPE_CHECKING:
    from .launch import ResultExplorerInstance, ResultExplorerWebSession

DEFAULT_RESULT_PROVIDER = "Local"
RX_SESSION_EXTENSION = ".rxs"


class GrpcStubWrapper:
    """Wrapper that automatically handles gRPC errors and injects metadata for insecure channels."""

    def __init__(self, stub, metadata=None):
        self._stub = stub
        self._metadata = metadata

    def __getattr__(self, name):
        attr = getattr(self._stub, name)

        # Only wrap callable methods (the actual gRPC service methods)
        if not callable(attr):
            return attr

        @wraps(attr)
        def wrapper(*args, **kwargs):
            # Inject metadata for insecure connections (for secure, it's in channel credentials)
            if self._metadata and "metadata" not in kwargs:
                kwargs["metadata"] = self._metadata
            try:
                return attr(*args, **kwargs)
            except grpc.RpcError as e:
                raise ResultExplorerError.from_grpc_error(e) from None

        return wrapper


class Client:
    def __init__(
        self,
        session_id: str,
        host: str = "localhost",
        grpc_port: int = 50000,
        ca_cert_path: str | Path | None = None,
        insecure: bool | None = None,
        custom_headers: list[tuple[str, str]] | None = None,
        instance: "ResultExplorerInstance | None" = None,
    ):
        """Initialize the client and connect to Result Explorer.


        Parameters
        ----------
        session_id : str
            Unique identifier for the Result Explorer session.
        host : str, optional
            Hostname or IP address of the Result Explorer API. Default is "localhost".
        grpc_port : int, optional
            Port number for the gRPC API. Default is 50000.
        ca_cert_path : str | Path, optional
            Path to CA certificate for secure gRPC connection.
            If not provided, connection will be insecure.
        insecure : bool, optional
            Whether to use an insecure gRPC connection.
            If None, will default to True if ca_cert_path is not provided.
        custom_headers : list of (str, str) tuples, optional
            Custom headers to include in gRPC requests,
            in addition to the session ID. Example: [("x-custom-header", "value")].
        instance : ResultExplorerInstance, optional
            Result Explorer instance to tie the client lifetime to. When the client
            is destroyed, the instance will be stopped as well.
        """

        self._host = host
        self._grpc_port = grpc_port
        self._session_id = session_id
        self._instance = instance
        self._grpc_metadata = [("x-session-id", self._session_id)]
        if custom_headers:
            self._grpc_metadata.extend(custom_headers)

        target = f"{self._host}:{self._grpc_port}"

        if insecure is None and ca_cert_path is None:
            warnings.warn(
                f"Using an insecure gRPC channel, unencrypted communication with {target}.",
                UnsecureConnectionWarning,
                stacklevel=2,
            )
            insecure = True

        wrapper_metadata = self._grpc_metadata

        if insecure:
            self._channel = grpc.insecure_channel(target)
        elif ca_cert_path is not None:
            with open(ca_cert_path, "rb") as f:
                trusted_ca = f.read()
            ssl_credentials = grpc.ssl_channel_credentials(root_certificates=trusted_ca)
            self._channel = grpc.secure_channel(target, ssl_credentials)
        else:
            raise ResultExplorerError(
                "Must provide either ca_cert_path for secure connection or set insecure=True."
            )

        # Wrap stubs to handle errors in a centralized way
        # To enable autocompletion on the stubs, we use a 'wrong' type annotation.
        self._solution_stub: solution_pb2_grpc.SolutionServiceStub = GrpcStubWrapper(
            solution_pb2_grpc.SolutionServiceStub(self._channel),
            metadata=wrapper_metadata,
        )  # type: ignore
        self._workspace_stub: workspace_pb2_grpc.WorkspaceServiceStub = GrpcStubWrapper(
            workspace_pb2_grpc.WorkspaceServiceStub(self._channel),
            metadata=wrapper_metadata,
        )  # type: ignore
        self._app_stub: app_pb2_grpc.AppServiceStub = GrpcStubWrapper(
            app_pb2_grpc.AppServiceStub(self._channel),
            metadata=wrapper_metadata,
        )  # type: ignore
        self._filesystem_stub: filesystem_pb2_grpc.FilesystemServiceStub = GrpcStubWrapper(
            filesystem_pb2_grpc.FilesystemServiceStub(self._channel),
            metadata=wrapper_metadata,
        )  # type: ignore
        self._hps_filesystem_stub: filesystem_pb2_grpc.HpsFilesystemServiceStub = GrpcStubWrapper(
            filesystem_pb2_grpc.HpsFilesystemServiceStub(self._channel),
            metadata=wrapper_metadata,
        )  # type: ignore

    def __del__(self):
        """Clean up resources when client is destroyed."""
        try:
            if self._instance is not None:
                self._instance.stop()
        except Exception:
            pass

    @property
    def instance(self) -> "ResultExplorerInstance | None":
        """Get the Result Explorer instance.

        Returns
        -------
        ResultExplorerInstance or None
            The Result Explorer instance if one is attached, None otherwise.
        """
        return self._instance

    @property
    def web_url(self) -> str | None:
        """Get the web UI URL.

        Returns
        -------
        str or None
            The URL of the web UI if an instance is attached and launched, None otherwise.
        """
        return self._instance.web_url if self._instance else None

    @property
    def web_session(self) -> "ResultExplorerWebSession | None":
        """Get the web session.

        Returns
        -------
        ResultExplorerWebSession or None
            The web session if an instance is attached, None otherwise.
        """
        return self._instance.web_session if self._instance else None

    def stop(self) -> None:
        """Stop the Result Explorer instance.

        Only effective if the client was created with an attached instance.
        """
        if self._instance is not None:
            self._instance.stop()
            self._instance = None

    @classmethod
    def connect_with_token(cls, token: str) -> "Client":
        """Connect with a base64 encoded json object that contains the connection info."""

        decoded_bytes = base64.b64decode(token)
        json_string = decoded_bytes.decode("utf-8")
        data = json.loads(json_string)

        host = data.get("host")
        grpc_port = data.get("grpcPort")
        session_id = data.get("sessionId")
        ca_cert_path = data.get("caCertPath", None)

        if host is None:
            raise ValueError("Token is missing 'host' information.")
        if grpc_port is None:
            raise ValueError("Token is missing 'grpcPort' information.")
        if session_id is None:
            raise ValueError("Token is missing 'sessionId' information.")

        return cls(host=host, grpc_port=grpc_port, session_id=session_id, ca_cert_path=ca_cert_path)

    # ----------- FileSystem methods ----------------
    def ls(
        self,
        path: str,
        result_provider: str | models.ResultProvider = DEFAULT_RESULT_PROVIDER,
        depth=0,
    ) -> list[models.FSItem]:
        rp_name = result_provider
        if isinstance(result_provider, models.ResultProvider):
            rp_name = result_provider.name

        req = models.LsRequest(result_provider_name=rp_name, path=path, max_depth=depth)
        res = self._filesystem_stub.Ls(req)
        return list(res.items)

    def hps_ls(
        self,
        path: str,
        result_provider: str | models.ResultProvider = DEFAULT_RESULT_PROVIDER,
    ) -> list[models.HpsFSItem]:
        """List entities in the HPS file system of the result provider.

        Parameters
        ----------

        path : str
            Path in the HPS file system to list. Use "/" for root.
            Otherwise, the path should be in the format "/project_id/job_id/task_id/file_id".

        """
        rp_name = result_provider
        if isinstance(result_provider, models.ResultProvider):
            rp_name = result_provider.name

        req = models.LsRequest(result_provider_name=rp_name, path=path)
        res = self._hps_filesystem_stub.Ls(req)
        return list(res.items)

    def _get_file_content(
        self,
        path: str,
        result_provider: str | models.ResultProvider = DEFAULT_RESULT_PROVIDER,
        lines_offset: int = 0,
    ) -> str:
        rp_name = result_provider
        if isinstance(result_provider, models.ResultProvider):
            rp_name = result_provider.name

        req = models.TailRequest(result_provider_name=rp_name, path=path, lines_offset=lines_offset)
        res = self._filesystem_stub.Tail(req)
        return res.content

    # ----------- Solution methods ----------------
    def create_solution(
        self,
        result_provider: str | models.ResultProvider,
        name: str,
        file_path: str,
        split_mesh_options: models.SplitMeshOptions | None = None,
    ) -> Solution:
        """Create a solution based on a file path. The file must be accessible by the server.

        Parameters
        ----------

        result_provider : str | models.ResultProvider
            Name of the result provider to use or a ResultProvider object.

        name : str
            Name of the solution to create.

        file_path : str
            Path to the result file. Must be accessible by the server.

        """

        rp_name = result_provider
        if isinstance(result_provider, models.ResultProvider):
            rp_name = result_provider.name

        file = models.File(path=file_path)
        split_mesh_options = split_mesh_options or models.SplitMeshOptions(auto_split_mesh=True)
        sol = models.SolutionCreate(
            result_provider_name=rp_name,
            name=name,
            files=[file],
            split_mesh_options=split_mesh_options,
        )
        pb_sol = self._solution_stub.Create(sol)
        return Solution(pb_sol, self)

    def create_hps_solution(
        self,
        result_provider: str | models.ResultProvider,
        name: str,
        project_id: str,
        task_id: str,
        file_id: str,
        split_mesh_options: models.SplitMeshOptions | None = None,
    ) -> Solution:
        """Create a solution based on a file in the HPS file system of the result provider.

        Parameters
        ----------
        result_provider : str | models.ResultProvider
            Name of the result provider to use or a ResultProvider object.
            Must have an hps_url defined.

        name : str
            Name of the solution to create.

        project_id : str
            HPS project ID where the file is located.

        task_id : str
            HPS task ID where the file is located.

        file_id : str
            HPS file ID of the file to load.

        """

        rp = None
        if isinstance(result_provider, models.ResultProvider):
            rp = result_provider
        else:
            rps = self.list_result_providers()
            rp = next((rp for rp in rps if rp.name == result_provider), None)
        if rp is None:
            raise ValueError(
                f"Result provider '{result_provider}' not found. "
                f"Available providers: {[rp.name for rp in rps]}"
            )

        if not rp.hps_url:
            raise ValueError(
                f"Result provider '{result_provider}' does not have an hps_url defined."
            )

        split_mesh_options = split_mesh_options or models.SplitMeshOptions(auto_split_mesh=True)
        files = models.HpsFiles(
            hps_url=rp.hps_url,
            project_id=project_id,
            files=[
                models.HpsFile(
                    task_id=task_id,
                    file_id=file_id,
                )
            ],
        )
        sol = models.SolutionCreate(
            result_provider_name=rp.name,
            name=name,
            hps_files=files,
            split_mesh_options=split_mesh_options,
        )
        pb_sol = self._solution_stub.Create(sol)
        return Solution(pb_sol, self)

    def list_solutions(self) -> list[Solution]:
        pb_list = self._solution_stub.List(models.Empty())
        return [Solution(s, self) for s in pb_list.solutions]

    def delete_solution(self, solution: Solution | str) -> None:
        """Delete a solution. Can pass Solution object or ID string."""
        solution_id = solution.id if isinstance(solution, Solution) else solution
        self._solution_stub.Delete(models.ResourceId(id=solution_id))

    def get_solution(self, solution_id: str) -> Solution:
        pb_sol = self._solution_stub.Get(models.ResourceId(id=solution_id))
        return Solution(pb_sol, self)

    # ----------- Workspace management ----------------

    def _create_workspace(self, name: str) -> Workspace:
        pb_ws = self._workspace_stub.Create(models.WorkspaceCreate(name=name))
        return Workspace(pb_ws, self)

    def create_workspace(self, name: str, rows: int = 1, cols: int = 1) -> Workspace:
        """Create a new workspace.

        If rows and cols are both 1, creates a single viewport.
        Otherwise creates a grid layout of viewports.
        """
        return _create_grid_workspace(self, name, rows, cols)

    def get_workspace(self, workspace_id: str) -> Workspace:
        pb_ws = self._workspace_stub.Get(models.ResourceId(id=workspace_id))
        return Workspace(pb_ws, self)

    def list_workspaces(self) -> list[Workspace]:
        pb_list = self._workspace_stub.List(models.Empty())
        return [Workspace(w, self) for w in pb_list.workspaces]

    def delete_workspace(self, workspace: str | Workspace) -> None:
        workspace_id = workspace.id if isinstance(workspace, Workspace) else workspace
        self._workspace_stub.Delete(models.ResourceId(id=workspace_id))

    def delete_viewport(self, viewport: str | Viewport) -> None:
        viewport_id = viewport.id if isinstance(viewport, Viewport) else viewport
        self._workspace_stub.DeleteViewport(models.ResourceId(id=viewport_id))

    def import_workspace_from_template(
        self,
        path: str | Path,
        *,
        workspace_name: str,
        solutions: list[models.WorkspaceImportRequest.SolutionInfo],
        use_camera_position: bool | None = None,
        use_time_freq: bool | None = None,
        use_body_visibility: bool | None = None,
    ) -> Workspace:
        """Create a workspace by importing a template file.

        Parameters
        ----------
        path : str | Path
            Path to the workspace template file (.rxwt).
        workspace_name : str
            Name for the new workspace.
        solutions : list[WorkspaceImportRequest.SolutionInfo]
            Solution bindings to use when importing.
        use_camera_position : bool, optional
            Whether to restore the camera position from the template.
        use_time_freq : bool, optional
            Whether to restore the time/frequency setting from the template.
        use_body_visibility : bool, optional
            Whether to restore body visibility from the template.

        Returns
        -------
        Workspace
            The newly created workspace.
        """
        return Workspace.import_from_template(
            self,
            path,
            workspace_name=workspace_name,
            solutions=solutions,
            use_camera_position=use_camera_position,
            use_time_freq=use_time_freq,
            use_body_visibility=use_body_visibility,
        )

    # ----------- App management ----------------
    def list_result_providers(self) -> list[models.ResultProvider]:
        r = self._app_stub.ListResultProviders(models.Empty())
        return list(r.result_providers)

    def create_result_provider(self, name: str, url: str) -> models.ResultProvider:
        req = models.CreateResultProviderRequest(name=name, url=url)
        return self._app_stub.CreateResultProvider(req)

    def delete_result_provider(self, result_provider: str | models.ResultProvider) -> None:
        rp_name = (
            result_provider.name
            if isinstance(result_provider, models.ResultProvider)
            else result_provider
        )
        self._app_stub.DeleteResultProvider(models.DeleteResultProviderRequest(name=rp_name))

    def authenticate_result_provider(
        self, result_provider: str | models.ResultProvider, token: str
    ) -> None:
        rp_name = (
            result_provider.name
            if isinstance(result_provider, models.ResultProvider)
            else result_provider
        )
        req = models.AuthenticateResultProviderRequest(result_provider_name=rp_name, token=token)
        self._app_stub.AuthenticateResultProvider(req)

    def app_info(self) -> models.AppInfo:
        return self._app_stub.GetAppInfo(models.Empty())

    def app_settings(self) -> models.AppSettings:
        return self._app_stub.GetAppSettings(models.Empty())

    def update_app_settings(self, settings: models.AppSettings) -> models.AppSettings:
        return self._app_stub.UpdateAppSettings(settings)

    def save_session(self, path: str | Path) -> None:
        """Save the current session to file.

        Parameters
        ----------
        path : str | Path
            Path to save the session file. Should end with .rxs extension.
        """
        path = Path(path)
        if path.suffix != RX_SESSION_EXTENSION:
            path = path.with_suffix(path.suffix + RX_SESSION_EXTENSION)
        path.parent.mkdir(parents=True, exist_ok=True)
        session = self._app_stub.SaveSession(models.Empty())
        with open(path, "w") as f:
            f.write(session.data)

    def open_session(self, path: str | Path) -> None:
        """Open a session from file.

        Parameters
        ----------
        path : str | Path
            Path to the session file. Should end with .rxs extension.
        """
        path = Path(path)
        if path.suffix != RX_SESSION_EXTENSION:
            raise ValueError(f"Session file should have '{RX_SESSION_EXTENSION}' extension.")
        with open(path) as f:
            data = f.read()
        self._app_stub.OpenSession(models.Session(data=data))


def _create_grid_workspace(client: Client, name, rows: int, cols: int):
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be >= 1")

    workspace = client._create_workspace(name=name or f"{cols}x{rows} Grid Workspace")

    if rows == 1 and cols == 1:
        return workspace

    column_viewports = [workspace.viewports[0]]
    for _ in range(cols - 1):
        source_column = column_viewports[-1]
        remaining_columns = cols - len(column_viewports)
        split_size = 100.0 * remaining_columns / (remaining_columns + 1)
        next_column = workspace.create_viewport(
            viewport=source_column,
            direction=models.ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
            size=split_size,
        )
        column_viewports.append(next_column)

    for column in column_viewports:
        parent = column
        for current_rows in range(1, rows):
            remaining_rows = rows - current_rows
            split_size = 100.0 * remaining_rows / (remaining_rows + 1)
            parent = workspace.create_viewport(
                viewport=parent,
                direction=models.ViewportDirection.VIEWPORT_DIRECTION_BOTTOM,
                size=split_size,
            )

    workspace = client.get_workspace(workspace.id)  # refresh workspace to get all viewports

    return workspace
