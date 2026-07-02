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
    BaseChartDisplayOptions,
    CameraPosition,
    ChartDisplayOptions,
    ChartView,
    ChartViewportMetadata,
    Component,
    ContactTrackersDisplayOptions,
    ContactTrackersViewportMetadata,
    ConvergenceTrackersDisplayOptions,
    ConvergenceTrackersViewportMetadata,
    DisplayOptions,
    Field,
    Location,
    LogsDisplayOptions,
    LogsViewportMetadata,
    MeshDisplayOptions,
    MeshView,
    MeshViewportMetadata,
    PlotDefinition,
    PlotDisplayOptions,
    PlotView,
    PlotViewportMetadata,
    ResultDisplayOptions,
    ResultFieldName,
    ResultType,
    ShellPosition,
    Solution,
    ThreeDDisplayOptions,
    View,
    Viewport,
    ViewportMetadata,
    Workspace,
)
