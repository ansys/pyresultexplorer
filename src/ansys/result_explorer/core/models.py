"""gRPC models for Result Explorer client."""

from ansys.api.result_explorer.v0.base_pb2 import Empty, ResourceId
from ansys.api.result_explorer.v0.server_models_pb2 import (
    AvailableMeshProperty,
    AvailableResult,
    Body,
    ChartDefinition,
    ConfigurableChart,
    ConfigurablePlot,
    File,
    HpsFile,
    PlotDefinition,
    ResultType,
    Solution,
    SolverTextOutputFile,
    SolverTextOutputType,
    SplitMeshOptions,
    TimeFrequency,
    View,
    ViewType,
)
from ansys.api.result_explorer.v0.solution_pb2 import (
    SolutionCreate,
    SolutionList,
)
from ansys.api.result_explorer.v0.workspace_pb2 import (
    CreateSnapshotRequest,
    CreateViewportRequest,
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
