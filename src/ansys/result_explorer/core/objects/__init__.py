# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
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
    BaseChartDisplayOptions,
    ChartDisplayOptions,
    ChartViewportMetadata,
    ContactTrackersDisplayOptions,
    ContactTrackersViewportMetadata,
    ConvergenceTrackersDisplayOptions,
    ConvergenceTrackersViewportMetadata,
    DisplayOptions,
    LogsDisplayOptions,
    LogsViewportMetadata,
    MeshDisplayOptions,
    MeshViewportMetadata,
    PlotDisplayOptions,
    PlotViewportMetadata,
    ResultDisplayOptions,
    ThreeDDisplayOptions,
    Viewport,
    ViewportMetadata,
)
from .workspace import Workspace

__all__ = [
    "BaseEntity",
    "BaseChartDisplayOptions",
    "ChartDisplayOptions",
    "ChartViewportMetadata",
    "CameraPosition",
    "ContactTrackersDisplayOptions",
    "ContactTrackersViewportMetadata",
    "ConvergenceTrackersDisplayOptions",
    "ConvergenceTrackersViewportMetadata",
    "LogsDisplayOptions",
    "LogsViewportMetadata",
    "MeshDisplayOptions",
    "MeshViewportMetadata",
    "NamedBaseEntity",
    "ResultDisplayOptions",
    "PlotDisplayOptions",
    "PlotViewportMetadata",
    "ThreeDDisplayOptions",
    "View",
    "PlotView",
    "ChartView",
    "MeshView",
    "DisplayOptions",
    "ViewportMetadata",
    "Viewport",
    "Solution",
    "Workspace",
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
