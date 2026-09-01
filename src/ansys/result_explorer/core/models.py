# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
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

"""gRPC models for Result Explorer client."""

from ansys.api.result_explorer.v0.app_pb2 import (
    AppInfo,
    AppSettings,
    AppTheme,
    AuthenticateResultProviderRequest,
    CreateResultProviderRequest,
    DataProcessingSettings,
    DeleteResultProviderRequest,
    ProcessingMode,
    ResultProvider,
    ResultProviderList,
    Session,
    ThreeDCameraProjection,
    ThreeDColorMap,
    ThreeDInteractionMode,
    ThreeDSettings,
)
from ansys.api.result_explorer.v0.base_pb2 import Empty, ResourceId
from ansys.api.result_explorer.v0.filesystem_pb2 import (
    FileContent,
    FilesystemRequest,
    FsItems,
    LsRequest,
    TailRequest,
)
from ansys.api.result_explorer.v0.server_models_pb2 import (
    AvailableMeshProperty,
    AvailableResult,
    Body,
    ChartDefinition,
    ChartDefinitionCreate,
    ChartResult,
    ChunkingStrategy,
    ConfigurableChart,
    ConfigurablePlot,
    CustomOptionsValue,
    ElementGroup,
    Field,
    File,
    Filter,
    FSItem,
    HpsFile,
    HpsFiles,
    HpsFSItem,
    IdsScoping,
    MeshGraphicsOptions,
    NamedSelection,
    NamedSelectionCreate,
    NamedSelectionDefinition,
    NamedSelectionType,
    PlotDefinition,
    PlotDefinitionCreate,
    PropertyScoping,
    Range,
    ResultType,
    ShellPosition,
    Solution,
    SolverNamedSelection,
    SolverTextOutputFile,
    SolverTextOutputType,
    SplitMeshOptions,
    StringMap,
    TimeFrequency,
    View,
    ViewType,
)
from ansys.api.result_explorer.v0.solution_pb2 import (
    CreateChartDefinitionRequest,
    CreateNamedSelectionRequest,
    CreatePlotDefinitionRequest,
    DeleteChartDefinitionRequest,
    DeleteNamedSelectionRequest,
    DeletePlotDefinitionRequest,
    SolutionCreate,
    SolutionList,
    UpdateChartDefinitionRequest,
    UpdateNamedSelectionRequest,
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
    WorkspaceImportRequest,
    WorkspaceList,
    WorkspaceUpdateRequest,
)
