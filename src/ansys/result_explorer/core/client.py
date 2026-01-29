import base64
import json
from functools import wraps

import grpc

from ansys.api.result_explorer.v0 import solution_pb2_grpc, workspace_pb2_grpc
from ansys.result_explorer.core import models

from .entities import Solution, Viewport, Workspace
from .exceptions import ResultExplorerError


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
        sol = models.SolutionCreate(
            result_provider_name=result_provider_name,
            name=name,
            files=[file],
            # split_mesh_options=split_mesh_options,
        )
        pb_sol = self._solution_stub.Create(sol, metadata=self._grpc_metadata)
        return Solution(pb_sol, self)

    def list_solutions(self) -> list[Solution]:
        pb_list = self._solution_stub.List(models.Empty(), metadata=self._grpc_metadata)
        return [Solution(s, self) for s in pb_list.solutions]

    def delete_solution(self, solution: Solution | str) -> None:
        """Delete a solution. Can pass Solution object or ID string."""
        solution_id = solution.id if isinstance(solution, Solution) else solution
        self._solution_stub.Delete(models.ResourceId(id=solution_id), metadata=self._grpc_metadata)

    def get_solution(self, solution_id: str) -> Solution:
        pb_sol = self._solution_stub.Get(
            models.ResourceId(id=solution_id), metadata=self._grpc_metadata
        )
        return Solution(pb_sol, self)

    # ----------- Workspace management ----------------

    def create_workspace(self, name: str) -> Workspace:
        pb_ws = self._workspace_stub.Create(
            models.WorkspaceCreate(name=name), metadata=self._grpc_metadata
        )
        return Workspace(pb_ws, self)

    def get_workspace(self, workspace_id: str) -> Workspace:
        pb_ws = self._workspace_stub.Get(
            models.ResourceId(id=workspace_id), metadata=self._grpc_metadata
        )
        return Workspace(pb_ws, self)

    def list_workspaces(self) -> list[Workspace]:
        pb_list = self._workspace_stub.List(models.Empty(), metadata=self._grpc_metadata)
        return [Workspace(w, self) for w in pb_list.workspaces]

    def delete_workspace(self, workspace: str | Workspace) -> None:
        workspace_id = workspace.id if isinstance(workspace, Workspace) else workspace
        self._workspace_stub.Delete(
            models.ResourceId(id=workspace_id), metadata=self._grpc_metadata
        )

    # def get_viewport(self, workspace_id: str, viewport_id: str) -> Viewport:
    #     # todo: implement a GetViewport method in the grpc service
    #     viewports = self.list_viewports(workspace_id=workspace_id)
    #     return next((v for v in viewports if v.id == viewport_id), None)

    def delete_viewport(self, viewport: str | Viewport) -> None:
        viewport_id = viewport.id if isinstance(viewport, Viewport) else viewport
        self._workspace_stub.DeleteViewport(
            models.ResourceId(id=viewport_id), metadata=self._grpc_metadata
        )
