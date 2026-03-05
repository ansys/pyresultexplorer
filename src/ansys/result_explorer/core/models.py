"""gRPC models for Result Explorer client."""

from ansys.api.result_explorer.v0.base_pb2 import Empty, ResourceId
from ansys.api.result_explorer.v0.server_models_pb2 import (
    AvailableMeshProperty,
    AvailableResult,
    Body,
    ChartDefinition,
    ChartDefinitionCreate,
    ConfigurableChart,
    ConfigurablePlot,
    ElementGroup,
    Field,
    File,
    Filter,
    HpsFile,
    NamedSelection,
    NamedSelectionType,
    PlotDefinition,
    PlotDefinitionCreate,
    ResultType,
    ShellPosition,
    Solution,
    SolverTextOutputFile,
    SolverTextOutputType,
    SplitMeshOptions,
    TimeFrequency,
    View,
    ViewType,
)
from ansys.api.result_explorer.v0.server_models_pb2 import (
    ChartResultInput as ChartResult,
)
from ansys.api.result_explorer.v0.solution_pb2 import (
    CreateChartDefinitionRequest,
    CreatePlotDefinitionRequest,
    DeleteChartDefinitionRequest,
    DeletePlotDefinitionRequest,
    SolutionCreate,
    SolutionList,
    UpdateChartDefinitionRequest,
    UpdatePlotDefinitionRequest,
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
