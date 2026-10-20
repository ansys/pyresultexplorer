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

"""Pythonic wrapper objects for gRPC models."""

from .base import BaseEntity, NamedBaseEntity
from .camera_position import CameraPosition
from .chart_definition import ChartDefinition, ChartResult, Filter
from .layout import ViewportPlacement, WorkspaceLayout
from .named_selection import (
    IdsScoping,
    NamedSelection,
    NamedSelectionCreate,
    NamedSelectionType,
    PropertyScoping,
    Range,
)
from .plot_definition import (
    Component,
    Field,
    Location,
    PlotDefinition,
    ResultFieldName,
    ResultType,
    ShellPosition,
)
from .solution import ChartView, MeshView, PlotView, Solution, View
from .viewport import (
    BaseChartViewportSettings,
    ChartViewportSettings,
    ContactTrackersViewportSettings,
    ConvergenceTrackersViewportSettings,
    LogsViewportSettings,
    MeshViewportSettings,
    PlotViewportMetadata,
    PlotViewportSettings,
    ThreeDViewportSettings,
    Viewport,
    ViewportMetadata,
    ViewportSettings,
)
from .workspace import Workspace

__all__ = [
    "BaseChartViewportSettings",
    "BaseEntity",
    "CameraPosition",
    "ChartDefinition",
    "ChartResult",
    "ChartView",
    "ChartViewportSettings",
    "Component",
    "ContactTrackersViewportSettings",
    "ConvergenceTrackersViewportSettings",
    "Field",
    "Filter",
    "IdsScoping",
    "Location",
    "LogsViewportSettings",
    "MeshView",
    "MeshViewportSettings",
    "NamedBaseEntity",
    "NamedSelection",
    "NamedSelectionCreate",
    "NamedSelectionType",
    "PlotDefinition",
    "PlotView",
    "PlotViewportMetadata",
    "PlotViewportSettings",
    "PropertyScoping",
    "Range",
    "ResultFieldName",
    "ResultType",
    "ShellPosition",
    "Solution",
    "ThreeDViewportSettings",
    "View",
    "Viewport",
    "ViewportMetadata",
    "ViewportPlacement",
    "ViewportSettings",
    "Workspace",
    "WorkspaceLayout",
]
