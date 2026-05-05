"""PyResultExplorer is a Python interface for Ansys Result Explorer."""

import importlib.metadata as importlib_metadata

__version__ = importlib_metadata.version(__name__.replace(".", "-"))

from .client import Client
from .exceptions import ResultExplorerError
from .logger import log
from .objects import (
    CameraPosition,
    ChartViewportMetadata,
    ContactTrackersViewportMetadata,
    ConvergenceTrackersViewportMetadata,
    LogsViewportMetadata,
    MeshViewportMetadata,
    PlotViewportMetadata,
    Solution,
    View,
    Viewport,
    ViewportMetadata,
    Workspace,
)
