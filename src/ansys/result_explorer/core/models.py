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

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit

from ansys.api.result_explorer.v0.app_pb2 import (
    AppInfo,
    AppSettings,
    AppTheme,
    AuthenticateResultProviderRequest,
    CreateResultProviderRequest,
    DataProcessingSettings,
    DeleteResultProviderRequest,
    GraphicsPrecision,
    OpenSessionRequest,
    ProcessingMode,
    ResultProvider,
    ResultProviderList,
    SaveSessionRequest,
    Session,
    SessionChunk,
    SessionImportOptions,
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
    SettingOption,
    SettingValue,
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


@dataclass
class HpsData:
    """Represents connection data specific to HPS."""

    grpc_resource_name: str

    def __post_init__(self) -> None:
        """Validate the field types."""
        if not isinstance(self.grpc_resource_name, str):
            raise ValueError("'grpc_resource_name' must be a string.")

    @classmethod
    def create(cls, input: dict[str, Any]) -> "HpsData":
        """Create an ``HpsData`` instance from a dictionary."""
        # Input values are untyped; __post_init__ validates them.
        return cls(
            grpc_resource_name=input.get("grpcResourceName", input.get("grpc_resource_name"))  # type: ignore
        )


@dataclass
class ConnectionToken:
    """Represents a connection token."""

    grpc_base_url: str
    session_id: str
    hps_data: HpsData | None = None
    ca_cert_path: str | None = None

    def __post_init__(self) -> None:
        """Validate the field types and the gRPC base URL."""
        if not isinstance(self.session_id, str):
            raise ValueError("'session_id' must be a string.")
        if not isinstance(self.hps_data, HpsData | None):
            raise ValueError("'hps_data' must be an HpsData instance or None.")
        if not isinstance(self.ca_cert_path, str | None):
            raise ValueError("'ca_cert_path' must be a string or None.")
        if not isinstance(self.grpc_base_url, str):
            raise ValueError("'grpc_base_url' must be a string.")
        url = urlsplit(self.grpc_base_url)
        try:
            port = url.port
        except ValueError:
            port = None
        if url.scheme not in ("http", "https") or not url.hostname or port is None:
            raise ValueError(
                "'grpc_base_url' must be an http(s) URL with a host and a port, "
                f"got {self.grpc_base_url!r}."
            )

    @classmethod
    def create(cls, input: dict[str, Any]) -> "ConnectionToken":
        """Create a ``ConnectionToken`` instance from a dictionary."""
        hps_data = input.get("hpsData", input.get("hps_data"))
        # Input values are untyped; __post_init__ validates them.
        return cls(
            grpc_base_url=input.get("grpcBaseUrl", input.get("grpc_base_url")),  # type: ignore
            session_id=input.get("sessionId", input.get("session_id")),  # type: ignore
            hps_data=HpsData.create(hps_data) if isinstance(hps_data, dict) else hps_data,
            ca_cert_path=input.get("caCertPath", input.get("ca_cert_path")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the token to a dictionary with snake_case keys."""
        return asdict(self)
