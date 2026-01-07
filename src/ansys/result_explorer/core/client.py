import base64
import json

import grpc
import requests

from ansys.api.result_explorer.v0 import solution_pb2_grpc, workspace_pb2_grpc
from ansys.result_explorer.core import models

from .models import (
    Empty,
    Solution,
    SolutionCreate,
    UpdateViewportRequest,
    Workspace,
    WorkspaceCreate,
)


class Client:
    def __init__(
        self,
        host="localhost",
        grpc_port=50000,
        http_port=8000,
        session_id: str | None = None,
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

    @classmethod
    def connect_with_token(cls, token: str):
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
        if http_port is None:
            raise ValueError("Token is missing 'httpPort' information.")
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
            split_mesh_options=split_mesh_options,
        )
        return self._solution_stub.Create(sol, metadata=self._grpc_metadata)

    def list_solutions(self) -> list[Solution]:
        return self._solution_stub.List(Empty(), metadata=self._grpc_metadata)

    # def get_views(self, solution_id: str) -> ViewList:
    #     return self._solution_stub.GetViews(
    #         ResourceId(id=solution_id), metadata=self._grpc_metadata
    #     )

    # ----------- Workspace methods ----------------

    def create_workspace(self, name: str) -> Workspace:
        return self._workspace_stub.Create(WorkspaceCreate(name=name), metadata=self._grpc_metadata)

    def list_workspaces(self) -> list[Workspace]:
        return self._workspace_stub.List(Empty(), metadata=self._grpc_metadata)

    def assign_view(self, viewport_id: str, solution_id: str, view_id: str) -> models.Viewport:
        """Assign a view to a viewport."""

        return self._workspace_stub.UpdateViewport(
            UpdateViewportRequest(
                viewport_id=viewport_id,
                solution_id=solution_id,
                view_id=view_id,
            ),
            metadata=self._grpc_metadata,
        )

    def take_snapshot(
        self, portal_id: str, settings: models.SnapshotSettings | None = None
    ) -> bytes:
        request = models.SnapshotRequest(
            portal_id=portal_id,
            settings=settings,
        )
        r = self._snapshot_stub.Create(request, metadata=self._grpc_metadata)
        return r.data
