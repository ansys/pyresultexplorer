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
    ChartViewportSettingOptions,
    ChartViewportSettings,
    ContactTrackersViewportSettingOptions,
    ContactTrackersViewportSettings,
    ConvergenceTrackersViewportSettingOptions,
    ConvergenceTrackersViewportSettings,
    LogsViewportSettingOptions,
    LogsViewportSettings,
    MeshViewportSettingOptions,
    MeshViewportSettings,
    PlotResultSettings,
    PlotViewportMetadata,
    PlotViewportSettingOptions,
    PlotViewportSettings,
    ThreeDViewportSettingOptions,
    ThreeDViewportSettings,
    Viewport,
    ViewportMetadata,
    ViewportSettingOptions,
    ViewportSettings,
)
from .workspace import Workspace

__all__ = [
    "BaseEntity",
    "BaseChartViewportSettings",
    "ChartViewportSettings",
    "ChartViewportSettingOptions",
    "CameraPosition",
    "ContactTrackersViewportSettings",
    "ContactTrackersViewportSettingOptions",
    "ConvergenceTrackersViewportSettings",
    "ConvergenceTrackersViewportSettingOptions",
    "LogsViewportSettings",
    "LogsViewportSettingOptions",
    "MeshViewportSettings",
    "MeshViewportSettingOptions",
    "NamedBaseEntity",
    "PlotResultSettings",
    "PlotViewportSettings",
    "PlotViewportMetadata",
    "PlotViewportSettingOptions",
    "ThreeDViewportSettings",
    "ThreeDViewportSettingOptions",
    "View",
    "PlotView",
    "ChartView",
    "MeshView",
    "ViewportSettings",
    "ViewportMetadata",
    "ViewportSettingOptions",
    "ViewportSettings",
    "Viewport",
    "ViewportPlacement",
    "Solution",
    "Workspace",
    "WorkspaceLayout",
    "PlotDefinition",
    "ResultType",
    "ShellPosition",
    "ResultFieldName",
    "Location",
    "Field",
    "Component",
    "ChartDefinition",
    "ChartResult",
    "Filter",
]
