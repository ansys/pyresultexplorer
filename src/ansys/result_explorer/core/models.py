"""gRPC models for Result Explorer client."""

from ansys.api.result_explorer.v0.base_pb2 import Empty, ResourceId
from ansys.api.result_explorer.v0.server_models_pb2 import (
    File,
    HpsFile,
    Solution,
    SplitMeshOptions,
    View,
    ViewType,
)
from ansys.api.result_explorer.v0.solution_pb2 import (
    SolutionCreate,
    SolutionList,
)
from ansys.api.result_explorer.v0.workspace_pb2 import (
    CreateSnapshotRequest,
    Snapshot,
    SnapshotSettings,
    SyncOptions,
    UpdateViewportRequest,
    Viewport,
    ViewportDirection,
    Workspace,
    WorkspaceCreate,
    WorkspaceList,
    WorkspaceUpdateRequest,
)
