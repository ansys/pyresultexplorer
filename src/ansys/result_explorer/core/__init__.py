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

"""PyResultExplorer is a Python interface for Ansys Result Explorer."""

import importlib.metadata as importlib_metadata

__version__ = importlib_metadata.version(__name__.replace(".", "-"))

from .client import Client
from .exceptions import ResultExplorerError
from .launch import (
    BrowserType,
    ResultExplorerInstance,
    ResultExplorerServerProcess,
    ResultExplorerWebSession,
    ServerLaunchConfig,
    WebLaunchConfig,
    launch_result_explorer,
)
from .logger import log
from .objects import (
    BaseChartViewportSettings,
    CameraPosition,
    ChartDefinition,
    ChartResult,
    ChartView,
    ChartViewportSettings,
    Component,
    ContactTrackersViewportSettings,
    ConvergenceTrackersViewportSettings,
    Field,
    Filter,
    Location,
    LogsViewportSettings,
    MeshView,
    MeshViewportSettings,
    PlotDefinition,
    PlotView,
    PlotViewportMetadata,
    PlotViewportSettings,
    ResultFieldName,
    ResultType,
    ShellPosition,
    Solution,
    ThreeDViewportSettings,
    View,
    Viewport,
    ViewportMetadata,
    ViewportPlacement,
    ViewportSettings,
    Workspace,
    WorkspaceLayout,
)
