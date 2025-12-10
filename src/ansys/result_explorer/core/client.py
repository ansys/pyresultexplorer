import grpc
import requests

from ansys.api.result_explorer.v0 import solution_pb2_grpc, workspace_pb2_grpc

from .models import AppSolution, Empty, SolutionCreate, Workspace, WorkspaceCreate


class Client:
    def __init__(
        self, host="localhost", grpc_port=50000, http_port=8000, session_id: str | None = None
    ):
        self._host = host
        self._grpc_port = grpc_port
        self._http_port = http_port
        self._session_id = session_id

        if self._session_id is None:
            data = requests.get(f"http://{self._host}:{self._http_port}/info").json()
            if len(data["sessions"]) == 0:
                raise Exception("No active sessions found. Please create a session first.")

            session_id = data["sessions"][0]["id"]  # hardcoded first session
            self._session_id = session_id

        self._grpc_metadata = [("x-session-id", self._session_id)]

        self._channel = grpc.insecure_channel(f"{self._host}:{self._grpc_port}")

        self._solution_stub = solution_pb2_grpc.SolutionServiceStub(self._channel)
        self._workspace_stub = workspace_pb2_grpc.WorkspaceServiceStub(self._channel)

    def create_solution(self, result_provider_name: str, name: str, file_path: str) -> AppSolution:
        sol = SolutionCreate(
            result_provider_name=result_provider_name,
            name=name,
            file_path=file_path,
        )
        return self._solution_stub.Create(sol, metadata=self._grpc_metadata)

    def list_solutions(self) -> list[AppSolution]:
        return self._solution_stub.List(Empty(), metadata=self._grpc_metadata)

    def create_workspace(self, name: str) -> Workspace:
        return self._workspace_stub.Create(WorkspaceCreate(name=name), metadata=self._grpc_metadata)

    def list_workspaces(self) -> list[Workspace]:
        return self._workspace_stub.List(Empty(), metadata=self._grpc_metadata)
