import base64
import json
from functools import wraps

import grpc

from ansys.api.result_explorer.v0 import solution_pb2_grpc, workspace_pb2_grpc
from ansys.result_explorer.core import models

from .exceptions import ResultExplorerError
from .models import (
    Empty,
    Solution,
    SolutionCreate,
    UpdateViewportRequest,
    ViewportDirection,
    Workspace,
    WorkspaceCreate,
)


class GrpcStubWrapper:
    """Wrapper that automatically handles gRPC errors for all stub method calls."""

    def __init__(self, stub):
        self._stub = stub

    def __getattr__(self, name):
        attr = getattr(self._stub, name)

        # Only wrap callable methods (the actual gRPC service methods)
        if not callable(attr):
            return attr

        @wraps(attr)
        def wrapper(*args, **kwargs):
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
        http_port: int | None = None,
    ):
        self._host = host
        self._grpc_port = grpc_port
        self._http_port = http_port
        self._session_id = session_id

        self._grpc_metadata = [("x-session-id", self._session_id)]

        self._channel = grpc.insecure_channel(f"{self._host}:{self._grpc_port}")

        # Wrap stubs to handle errors in a centralized way
        # To enable autocompletion on the stubs, we use a 'wrong' type annotation.
        self._solution_stub: solution_pb2_grpc.SolutionServiceStub = GrpcStubWrapper(
            solution_pb2_grpc.SolutionServiceStub(self._channel)
        )  # type: ignore
        self._workspace_stub: workspace_pb2_grpc.WorkspaceServiceStub = GrpcStubWrapper(
            workspace_pb2_grpc.WorkspaceServiceStub(self._channel)
        )  # type: ignore

    @classmethod
    def connect_with_token(cls, token: str) -> "Client":
        """Connect with a base64 encoded json object that contains the connection info."""

        decoded_bytes = base64.b64decode(token)
        json_string = decoded_bytes.decode("utf-8")
        data = json.loads(json_string)

        host = data.get("host")
        http_port = data.get("httpPort")
        grpc_port = data.get("grpcPort")
        session_id = data.get("sessionId")

        if host is None:
            raise ValueError("Token is missing 'host' information.")
        if grpc_port is None:
            raise ValueError("Token is missing 'grpcPort' information.")
        if session_id is None:
            raise ValueError("Token is missing 'sessionId' information.")

        return cls(host=host, grpc_port=grpc_port, http_port=http_port, session_id=session_id)

    # ----------- Solution methods ----------------
    def create_solution(
        self,
        result_provider_name: str,
        name: str,
        file_path: str,
        split_mesh_options: models.SplitMeshOptions | None = None,
    ) -> Solution:
        file = models.File(path=file_path)
        sol = SolutionCreate(
            result_provider_name=result_provider_name,
            name=name,
            files=[file],
            # split_mesh_options=split_mesh_options,
        )
        return self._solution_stub.Create(sol, metadata=self._grpc_metadata)

    def list_solutions(self) -> list[Solution]:
        return self._solution_stub.List(Empty(), metadata=self._grpc_metadata).solutions

    def delete_solution(self, solution_id: str) -> None:
        self._solution_stub.Delete(models.ResourceId(id=solution_id), metadata=self._grpc_metadata)

    def get_solution(self, solution_id: str) -> Solution:
        return self._solution_stub.Get(
            models.ResourceId(id=solution_id), metadata=self._grpc_metadata
        )

    # ----------- Workspace management ----------------

    def create_workspace(self, name: str) -> Workspace:
        return self._workspace_stub.Create(WorkspaceCreate(name=name), metadata=self._grpc_metadata)

    def get_workspace(self, workspace_id: str) -> Workspace:
        return self._workspace_stub.Get(
            models.ResourceId(id=workspace_id), metadata=self._grpc_metadata
        )

    def list_workspaces(self) -> list[Workspace]:
        return list(self._workspace_stub.List(Empty(), metadata=self._grpc_metadata).workspaces)

    def delete_workspace(self, workspace_id: str) -> None:
        self._workspace_stub.Delete(
            models.ResourceId(id=workspace_id), metadata=self._grpc_metadata
        )

    def set_fullscreen_viewport(self, workspace_id: str, viewport_id: str) -> Workspace:
        request = models.WorkspaceUpdateRequest(
            workspace_id=workspace_id,
            fullscreen_viewport_id=viewport_id,
        )
        return self._workspace_stub.Update(request, metadata=self._grpc_metadata)

    def exit_fullscreen(self, workspace_id: str) -> Workspace:
        request = models.WorkspaceUpdateRequest(
            workspace_id=workspace_id,
            fullscreen_viewport_id="",
        )
        return self._workspace_stub.Update(request, metadata=self._grpc_metadata)

    def set_workspace_sync(
        self,
        workspace_id: str,
        camera: bool | None = None,
        time_freq: bool | None = None,
        legend: bool | None = None,
    ) -> Workspace:
        sync = models.SyncOptions(
            camera=camera,
            time_freq=time_freq,
            legend=legend,
        )
        request = models.WorkspaceUpdateRequest(
            workspace_id=workspace_id,
            sync_options=sync,
        )
        return self._workspace_stub.Update(request, metadata=self._grpc_metadata)

    # ----------- Viewport management ----------------
    def assign_view(
        self, viewport_id: str, solution_id: str, view_id: str, wait: bool = True
    ) -> models.Viewport:
        """Assign a view to a viewport."""

        return self._workspace_stub.UpdateViewport(
            UpdateViewportRequest(
                viewport_id=viewport_id,
                solution_id=solution_id,
                view_id=view_id,
                wait=wait,
            ),
            metadata=self._grpc_metadata,
        )

    def modify_view_metadata(
        self, viewport_id: str, metadata: dict, wait: bool = True
    ) -> models.Viewport:
        """Assign a view to a viewport."""

        return self._workspace_stub.UpdateViewport(
            UpdateViewportRequest(
                viewport_id=viewport_id,
                metadata=metadata,
                wait=wait,
            ),
            metadata=self._grpc_metadata,
        )

    def take_snapshot(
        self, viewport_id: str, settings: models.SnapshotSettings | None = None
    ) -> bytes:
        request = models.CreateSnapshotRequest(
            viewport_id=viewport_id,
            settings=settings,
        )
        r = self._workspace_stub.CreateSnapshot(request, metadata=self._grpc_metadata)
        return r.data

    def list_viewports(self, workspace_id: str) -> list[models.Viewport]:
        return self._workspace_stub.ListViewports(
            models.ResourceId(id=workspace_id), metadata=self._grpc_metadata
        ).viewports

    def get_viewport(self, workspace_id: str, viewport_id: str) -> models.Viewport:
        # todo: implement a GetViewport method in the grpc service
        viewports = self.list_viewports(workspace_id=workspace_id)
        return next((v for v in viewports if v.id == viewport_id), None)

    def create_viewport(
        self, workspace_id: str, viewport_id: str, direction: ViewportDirection
    ) -> models.Viewport:
        return self._workspace_stub.CreateViewport(
            models.CreateViewportRequest(
                workspace_id=workspace_id,
                viewport_id=viewport_id,
                direction=direction,
            ),
            metadata=self._grpc_metadata,
        )

    def delete_viewport(self, viewport_id: str) -> None:
        self._workspace_stub.DeleteViewport(
            models.ResourceId(id=viewport_id), metadata=self._grpc_metadata
        )
