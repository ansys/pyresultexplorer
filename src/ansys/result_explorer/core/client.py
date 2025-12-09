import grpc

from ansys.api.result_explorer.v0 import solution_pb2_grpc, workspace_pb2_grpc

from .models import AppSolution, Empty, SolutionCreate, Workspace, WorkspaceCreate


class Client:
    def __init__(self, host="localhost", port=50000):
        self._target = f"{host}:{port}"
        self._channel = grpc.insecure_channel(self._target)

        self._solution_stub = solution_pb2_grpc.SolutionServiceStub(self._channel)
        self._workspace_stub = workspace_pb2_grpc.WorkspaceServiceStub(self._channel)

    def create_solution(self, result_provider_name: str, name: str, file_path: str) -> AppSolution:
        sol = SolutionCreate(
            result_provider_name=result_provider_name,
            name=name,
            file_path=file_path,
        )
        return self._solution_stub.Create(sol)

    def list_solutions(self) -> list[AppSolution]:
        return self._solution_stub.List(Empty())

    def create_workspace(self, name: str) -> Workspace:
        return self._workspace_stub.Create(WorkspaceCreate(name=name))

    def list_workspaces(self) -> list[Workspace]:
        return self._workspace_stub.List(Empty())
