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

"""Viewport entity and metadata classes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict, ParseDict

from .. import models
from .base import BaseEntity
from .camera_position import CameraPosition

if TYPE_CHECKING:
    from ..client import Client
    from .solution import View


class PbProperty:
    """Descriptor for accessing nested protobuf object properties.

    Supports dot-notation for nested keys (e.g., "explodeSettings.active").
    """

    def __init__(self, key: str):
        """Initialize descriptor with property key path."""
        self.key = key

    def __get__(self, obj, objtype=None):
        """Get property value from nested protobuf object."""
        if obj is None:
            return self
        return self._get_nested(obj._pb_obj, self.key)

    def __set__(self, obj, value):
        """Set property value on nested protobuf object."""
        self._set_nested(obj._pb_obj, self.key, value)

    @staticmethod
    def _get_nested(obj, path: str):
        """Get nested value using dot notation."""
        for k in path.split("."):
            obj = obj[k]
        return obj

    @staticmethod
    def _set_nested(obj, path: str, value):
        """Set nested value using dot notation."""
        keys = path.split(".")
        for k in keys[:-1]:
            obj = obj[k]
        obj[keys[-1]] = value


class PbPropertyReadOnly:
    """Read-only descriptor for accessing nested protobuf object properties.

    Supports dot-notation for nested keys.
    Raises AttributeError on write attempts.
    """

    def __init__(self, key: str):
        """Initialize read-only descriptor with property key path."""
        self.key = key

    def __get__(self, obj, objtype=None):
        """Get read-only property value from nested protobuf object."""
        if obj is None:
            return self
        return PbProperty._get_nested(obj._pb_obj, self.key)

    def __set__(self, obj, value):
        """Prevent setting value on read-only property."""
        raise AttributeError(
            f"Property '{self.key}' of '{type(obj).__name__}' object is read-only."
        )


class ViewportMetadata:
    """Read-only wrapper for viewport metadata."""

    def __init__(self, pb_obj: models.Viewport, client: Client, solution_id: str | None = None):
        """Initialize viewport metadata wrapper."""
        self._pb_obj = pb_obj
        self._client = client
        self._solution_id = solution_id

    def __str__(self):
        """Return metadata as formatted JSON string."""
        return json.dumps(MessageToDict(self._pb_obj), indent=2)


class MeshViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to mesh viewports."""

    pass


class LegendSettings:
    """Read-only legend display settings for a plot result.

    Controls colors, range, and discretization.
    """

    use_global_min_max: bool = PbPropertyReadOnly("useGlobalMinMax")
    range: list[float] = PbPropertyReadOnly("range")

    def __init__(self, pb_obj):
        """Initialize legend settings wrapper."""
        self._pb_obj = pb_obj


@dataclass(frozen=True)
class ResultExtreme:
    """Minimum or maximum extreme of a plot result."""

    value: float
    """Scalar result value."""
    entity_id: int | None
    """ID of the entity (node/element) at the extreme."""
    position: tuple[float, float, float] | None
    """World-space position (x, y, z) of the extreme."""
    displacement: tuple[float, float, float] | None
    """Displacement vector (x, y, z) at the extreme."""

    @classmethod
    def _from_pb(cls, pb_obj) -> ResultExtreme:
        """Build from a protobuf struct object."""
        pos = pb_obj["position"] if "position" in pb_obj else None
        disp = pb_obj["displacement"] if "displacement" in pb_obj else None
        return cls(
            # default to 0.0 if value is missing
            # because originally this comes from a graphics-data pb where value is a required float,
            # which gets not included in the dict if it's not set
            value=pb_obj["value"] if "value" in pb_obj else 0.0,
            entity_id=int(pb_obj["entityId"]) if "entityId" in pb_obj else None,
            position=(
                pos["x"] if "x" in pos else 0.0,
                pos["y"] if "y" in pos else 0.0,
                pos["z"] if "z" in pos else 0.0,
            )
            if pos is not None
            else None,
            displacement=(
                disp["x"] if "x" in disp else 0.0,
                disp["y"] if "y" in disp else 0.0,
                disp["z"] if "z" in disp else 0.0,
            )
            if disp is not None
            else None,
        )


class ActiveResult:
    """Read-only active result currently displayed in a plot viewport."""

    result_name: str = PbPropertyReadOnly("resultName")
    time_set_index: int = PbPropertyReadOnly("timeSetIndex")
    component_index: int = PbPropertyReadOnly("componentIndex")
    type: str = PbPropertyReadOnly("type")
    result_index: int = PbPropertyReadOnly("resultIndex")
    set_id: int = PbPropertyReadOnly("setId")
    data_array_name: str = PbPropertyReadOnly("dataArrayName")
    range: list[float] = PbPropertyReadOnly("range")

    def __init__(self, pb_obj):
        """Initialize active result wrapper."""
        self._pb_obj = pb_obj

    @property
    def legend(self) -> LegendSettings:
        """Legend settings for this result."""
        return LegendSettings(self._pb_obj["legend"])

    @property
    def _extremes(self) -> list[ResultExtreme]:
        """Min/max extremes of the result."""
        if "extremes" not in self._pb_obj:
            return []
        return [ResultExtreme._from_pb(e) for e in self._pb_obj["extremes"]]

    @property
    def min(self) -> ResultExtreme | None:
        """Minimum extreme of the result, or None if not available."""
        extremes = self._extremes
        if not extremes:
            return None
        return min(extremes, key=lambda e: e.value)

    @property
    def max(self) -> ResultExtreme | None:
        """Maximum extreme of the result, or None if not available."""
        extremes = self._extremes
        if not extremes:
            return None
        return max(extremes, key=lambda e: e.value)


class PlotViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to plot viewports."""

    @property
    def active_result(self) -> ActiveResult | None:
        """Active result currently displayed, or None if not set."""
        if "activeResult" not in self._pb_obj:
            return None
        return ActiveResult(self._pb_obj["activeResult"])


class BaseChartViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to base chart viewports."""

    @property
    def series_names(self) -> list[str]:
        """List of all available series names."""
        return [s.string_value for s in self._pb_obj["displayOptions"]["seriesNames"].values]


class ChartViewportMetadata(BaseChartViewportMetadata):
    """Read-only metadata specific to chart viewports."""

    @property
    def chart_names(self) -> list[str]:
        """List of all available chart names."""
        return [s.string_value for s in self._pb_obj["displayOptions"]["chartNames"].values]


class ContactTrackersViewportMetadata(BaseChartViewportMetadata):
    """Read-only metadata specific to contact trackers viewports."""

    @property
    def contact_tracker_names(self) -> list[str]:
        """List of all available contact tracker names."""
        return [s.string_value for s in self._pb_obj["displayOptions"]["chartNames"].values]


class ConvergenceTrackersViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to convergence trackers viewports."""

    pass


class LogsViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to logs viewports."""

    pass


# ---------------------------------------------------------------------------
# PlotDisplayOptions dataclass
# ---------------------------------------------------------------------------


@dataclass
class ResultDisplayOptions:
    """Result-specific display options for plot viewports.

    These are sent to the server via the
    ``UpdateViewportRequest.display_options`` field.

    Parameters
    ----------
    result : str, optional
        Result name to display.
    set_id : int, optional
        Actual set ID (from ``TimeFrequency.set_id``), not an index.
    component_index : int, optional
        Component index for the result.
    deformation_scale : float, optional
        Deformation scale factor.
    legend_range : tuple of float, optional
        Custom legend range as ``(min, max)``.
    use_global_min_max : bool, optional
        Whether to use the global min/max for the legend range.

    Examples
    --------
    >>> from ansys.result_explorer.core import ResultDisplayOptions
    >>> opts = ResultDisplayOptions(component_index=2, deformation_scale=3.0)

    """

    result: str | None = None
    set_id: int | None = None
    component_index: int | None = None
    deformation_scale: float | None = None
    legend_range: tuple[float, float] | None = None
    use_global_min_max: bool | None = None

    @classmethod
    def _from_pb(cls, pb_obj) -> ResultDisplayOptions:
        """Build from active result and deformation_scale in metadata Struct."""
        if "activeResult" not in pb_obj:
            return cls()

        ar = pb_obj["activeResult"]
        legend = ar["legend"] if "legend" in ar else {}
        raw_range = legend["range"] if "range" in legend else None
        legend_range = None
        if raw_range is not None and len(raw_range) == 2:
            legend_range = (float(raw_range[0]), float(raw_range[1]))

        return cls(
            result=ar["resultName"] if "resultName" in ar else None,
            set_id=int(ar["setId"]) if "setId" in ar else None,
            component_index=int(ar["componentIndex"]) if "componentIndex" in ar else None,
            deformation_scale=(
                float(pb_obj["deformationScale"]) if "deformationScale" in pb_obj else None
            ),
            legend_range=legend_range,
            use_global_min_max=(
                bool(legend["useGlobalMinMax"]) if "useGlobalMinMax" in legend else None
            ),
        )

    def to_pb(self) -> struct_pb2.Struct:
        """Serialize to a protobuf Struct (only non-None fields).

        Returns
        -------
        google.protobuf.struct_pb2.Struct
            Struct for ``UpdateViewportRequest.display_options``.

        """
        d: dict = {}
        if self.result is not None:
            d["result"] = self.result
        if self.set_id is not None:
            d["setId"] = self.set_id
        if self.component_index is not None:
            d["componentIndex"] = self.component_index
        if self.deformation_scale is not None:
            d["deformationScale"] = self.deformation_scale
        if self.legend_range is not None:
            d["legendRange"] = list(self.legend_range)
        if self.use_global_min_max is not None:
            d["useGlobalMinMax"] = self.use_global_min_max
        s = struct_pb2.Struct()
        ParseDict(d, s)
        return s


# ---------------------------------------------------------------------------
# Viewport display options classes (read/write)
# ---------------------------------------------------------------------------


class DisplayOptions:
    """Read/write wrapper for viewport display options."""

    def __init__(self, pb_obj, client: Client, solution_id: str | None = None):
        """Initialize viewport display options wrapper."""
        self._pb_obj = pb_obj
        self._client = client
        self._solution_id = solution_id

    def to_pb(self):
        """Return the underlying protobuf Struct for metadata updates.

        Returns
        -------
        google.protobuf.struct_pb2.Struct
            The metadata Struct for ``UpdateViewportRequest.metadata``.

        """
        return self._pb_obj

    @classmethod
    def _from_pb(cls, pb_obj, client: Client, solution_id: str | None = None) -> DisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)

    def __str__(self):
        """Return display options as formatted JSON string."""
        return json.dumps(MessageToDict(self._pb_obj), indent=2)


class ThreeDDisplayOptions(DisplayOptions):
    """Read/write display options for 3D viewports."""

    show_mesh_edges: bool = PbProperty("showMeshEdges")
    explode: bool = PbProperty("explodeSettings.active")
    explode_scale_factor: float = PbProperty("explodeSettings.scaleFactor")
    explode_direction: Literal["Radial", "X", "Y", "Z"] = PbProperty("explodeSettings.direction")
    expanded_groups: list[str] = PbProperty("expandedGroups")
    visible_bodies: list[str] = PbProperty("shownBodies")

    @property
    def camera_position(self) -> CameraPosition | None:
        """Current camera position, or None if not set."""
        if "cameraPosition" not in self._pb_obj:
            return None
        raw = self._pb_obj["cameraPosition"]
        return CameraPosition(list(raw["matrix"]))

    @camera_position.setter
    def camera_position(self, value: CameraPosition) -> None:
        """Set the camera position."""
        self._pb_obj["cameraPosition"] = {"matrix": value.matrix}

    @classmethod
    def _from_pb(
        cls, pb_obj, client: Client, solution_id: str | None = None
    ) -> ThreeDDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


class MeshDisplayOptions(ThreeDDisplayOptions):
    """Read/write display options for mesh viewports."""

    @property
    def visible_named_selection(self) -> str | None:
        """Currently visible named selection in this viewport."""
        return self._pb_obj["shownNamedSelection"]

    @visible_named_selection.setter
    def visible_named_selection(self, value: str | models.NamedSelection | None) -> None:
        """Set the visible named selection in this viewport.

        Parameters
        ----------
        value : str or NamedSelection, optional
            The named selection to show. Can be specified by id, name or
            by passing a NamedSelection object. If None, no named
            selection will be shown.

        """
        if value is None:
            self._pb_obj["shownNamedSelection"] = None
            return

        solution = self._client.get_solution(self._solution_id)

        ns = None
        if isinstance(value, models.NamedSelection):
            ns = value

        if ns is None:
            ns = next((ns for ns in solution.named_selections if ns.id == value), None)

        if ns is None:
            ns = next((ns for ns in solution.named_selections if ns.name == value), None)

        if ns is None:
            raise ValueError(f"No named selection with id or name '{value}' found in solution.")

        self._pb_obj["shownNamedSelection"] = ns.id

    @classmethod
    def _from_pb(cls, pb_obj, client: Client, solution_id: str | None = None) -> MeshDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


class PlotDisplayOptions(ThreeDDisplayOptions):
    """Read/write display options for plot viewports.

    The ``result_options`` field holds result-specific options
    such as the active result, component, and deformation scale.
    """

    show_min_max_labels: bool = PbProperty("showMinMaxLabels")

    def __init__(
        self,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        result_options: ResultDisplayOptions | None = None,
    ):
        """Initialize plot viewport display options."""
        super().__init__(pb_obj, client, solution_id)
        self.result_options = result_options

    @classmethod
    def _from_pb(cls, pb_obj, client: Client, solution_id: str | None = None) -> PlotDisplayOptions:
        """Build from a metadata Struct, populating result_options."""
        return cls(
            pb_obj, client, solution_id, result_options=ResultDisplayOptions._from_pb(pb_obj)
        )


class BaseChartDisplayOptions(DisplayOptions):
    """Read/write display options for base chart viewports."""

    show_legend: bool = PbProperty("displayOptions.showLegend")
    show_table: bool = PbProperty("displayOptions.showTable")
    split_direction: Literal["horizontal", "vertical"] = PbProperty("displayOptions.splitDirection")

    @property
    def series_names(self) -> list[str]:
        """List of all available series names."""
        return [s.string_value for s in self._pb_obj["displayOptions"]["seriesNames"].values]

    @property
    def active_series(self) -> list[str]:
        """List of currently active series."""
        indices = self._pb_obj["displayOptions"]["activeSeriesIndices"]
        return [self.series_names[int(idx)] for idx in indices]

    @active_series.setter
    def active_series(self, names: list[str]) -> None:
        """Set the active series.

        Parameters
        ----------
        names : list[str]
            List of series names to make active.

        """
        for name in names:
            if name not in self.series_names:
                raise ValueError(f"Invalid series name: {name}")
        indices = [self.series_names.index(name) for name in names]
        self._pb_obj["displayOptions"]["activeSeriesIndices"] = indices

    @classmethod
    def _from_pb(
        cls, pb_obj, client: Client, solution_id: str | None = None
    ) -> BaseChartDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


class ChartDisplayOptions(BaseChartDisplayOptions):
    """Read/write display options for chart viewports."""

    @property
    def chart_names(self) -> list[str]:
        """List of all available chart names."""
        return [s.string_value for s in self._pb_obj["displayOptions"]["chartNames"].values]

    @property
    def active_charts(self) -> list[str]:
        """List of currently active charts."""
        indices = self._pb_obj["displayOptions"]["activeChartIndices"]
        return [self.chart_names[int(idx)] for idx in indices]

    @active_charts.setter
    def active_charts(self, names: list[str]) -> None:
        """Set the active charts.

        Parameters
        ----------
        names : list[str]
            List of chart names to make active.

        """
        for name in names:
            if name not in self.chart_names:
                raise ValueError(f"Invalid chart name: {name}")
        indices = [self.chart_names.index(name) for name in names]
        self._pb_obj["displayOptions"]["activeChartIndices"] = indices

    @property
    def selected_x_axis(self) -> str:
        """Name of the currently selected x-axis series."""
        idx = int(self._pb_obj["displayOptions"]["selectedXAxisIndex"])
        return self.series_names[idx]

    @selected_x_axis.setter
    def selected_x_axis(self, name: str) -> None:
        """Set the x-axis series.

        Parameters
        ----------
        name : str
            Name of the series to use as the x-axis.

        """
        if name not in self.series_names:
            raise ValueError(f"Invalid x-axis name: {name}")
        idx = self.series_names.index(name)
        self._pb_obj["displayOptions"]["selectedXAxisIndex"] = idx

    @classmethod
    def _from_pb(
        cls, pb_obj, client: Client, solution_id: str | None = None
    ) -> ChartDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


class ContactTrackersDisplayOptions(BaseChartDisplayOptions):
    """Read/write display options for contact trackers viewports."""

    @property
    def contact_tracker_names(self) -> list[str]:
        """List of all available contact tracker names."""
        return [s.string_value for s in self._pb_obj["displayOptions"]["chartNames"].values]

    @property
    def active_contact_trackers(self) -> list[str]:
        """List of currently active contact trackers."""
        indices = self._pb_obj["displayOptions"]["activeChartIndices"]
        return [self.contact_tracker_names[int(idx)] for idx in indices]

    @active_contact_trackers.setter
    def active_contact_trackers(self, names: list[str]) -> None:
        """Set the active contact trackers.

        Parameters
        ----------
        names : list[str]
            List of contact tracker names to make active.

        """
        for name in names:
            if name not in self.contact_tracker_names:
                raise ValueError(f"Invalid contact tracker name: {name}")
        indices = [self.contact_tracker_names.index(name) for name in names]
        self._pb_obj["displayOptions"]["activeChartIndices"] = indices

    @classmethod
    def _from_pb(
        cls, pb_obj, client: Client, solution_id: str | None = None
    ) -> ContactTrackersDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


class ConvergenceTrackersDisplayOptions(DisplayOptions):
    """Read/write display options for convergence trackers viewports."""

    selected_tracker_name: str = PbProperty("selectedTrackerName")

    @classmethod
    def _from_pb(
        cls, pb_obj, client: Client, solution_id: str | None = None
    ) -> ConvergenceTrackersDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


class LogsDisplayOptions(DisplayOptions):
    """Read/write display options for logs viewports."""

    log_path: str = PbProperty("currentLogPath")

    @classmethod
    def _from_pb(cls, pb_obj, client: Client, solution_id: str | None = None) -> LogsDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id)


# ---------------------------------------------------------------------------
# Viewport entity
# ---------------------------------------------------------------------------


class Viewport(BaseEntity[models.Viewport]):
    """Represents a viewport in a workspace."""

    @property
    def solution_id(self) -> str | None:
        """ID of the solution assigned to this viewport."""
        return self._pb.solution_id

    @property
    def view_id(self) -> str | None:
        """ID of the view assigned to this viewport."""
        return self._pb.view_id

    @property
    def ready(self) -> bool:
        """Whether the viewport is ready."""
        return self._pb.ready

    def _resolve_view(self) -> View | None:
        """Resolve the assigned view from solution views."""
        if self.view_id and self.solution_id:
            solution = self._client.get_solution(self.solution_id)
            return next((v for v in solution.views if v.id == self.view_id), None)
        return None

    @property
    def view(self) -> View | None:
        """Get the assigned view, if any."""
        return self._resolve_view()

    @property
    def metadata(self) -> ViewportMetadata:
        """Read-only viewport metadata (server-computed state)."""
        view = self._resolve_view()
        pb_obj = self._pb.metadata

        if view is None:
            return ViewportMetadata(pb_obj, self._client, self.solution_id)

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            return PlotViewportMetadata(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            return ChartViewportMetadata(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            return MeshViewportMetadata(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            return ConvergenceTrackersViewportMetadata(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            return ContactTrackersViewportMetadata(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_LOGS:
            return LogsViewportMetadata(pb_obj, self._client, self.solution_id)

        return ViewportMetadata(pb_obj, self._client, self.solution_id)

    @property
    def display_options(self) -> DisplayOptions:
        """Read/write viewport display options."""
        view = self._resolve_view()
        pb_obj = self._pb.metadata

        if view is None:
            return DisplayOptions._from_pb(pb_obj, self._client, self.solution_id)

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            return PlotDisplayOptions._from_pb(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            return ChartDisplayOptions._from_pb(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            return MeshDisplayOptions._from_pb(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            return ConvergenceTrackersDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id
            )
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            return ContactTrackersDisplayOptions._from_pb(pb_obj, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_LOGS:
            return LogsDisplayOptions._from_pb(pb_obj, self._client, self.solution_id)

        return DisplayOptions._from_pb(pb_obj, self._client, self.solution_id)

    def set_display_options(self, opts: DisplayOptions) -> None:
        """Apply display options to this viewport.

        Parameters
        ----------
        opts : DisplayOptions
            Display options to apply. Obtain via
            ``viewport.display_options``, modify as needed,
            then pass back here.

        """
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            metadata=opts.to_pb(),
            wait=True,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(req)

        if isinstance(opts, PlotDisplayOptions) and opts.result_options is not None:
            req.display_options.CopyFrom(opts.result_options.to_pb())
            self._pb = self._client._workspace_stub.UpdateViewport(req)

    @property
    def size(self) -> float:
        """Size of the viewport as a percentage of its parent."""
        return self._pb.size

    def set_view(self, view: View, wait: bool = True) -> Viewport:
        """Assign a view to this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            solution_id=view.solution.id,
            view_id=view.id,
            wait=wait,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(req)
        return self

    def take_snapshot(self, settings: models.SnapshotSettings | None = None) -> bytes:
        """Take a snapshot of this viewport.

        Parameters
        ----------
        settings : SnapshotSettings, optional
            Snapshot settings to control what elements appear in the image
            (timestamp, logo, legend, solution name, etc.). If None, uses server defaults.

        Returns
        -------
        bytes
            PNG image data.

        """
        req = models.CreateSnapshotRequest(viewport_id=self.id)
        if settings is not None:
            req.settings.CopyFrom(settings)
        snapshot = self._client._workspace_stub.CreateSnapshot(req)
        return snapshot.data

    def set_size(self, size: float) -> None:
        """Set the size of this viewport in the workspace layout."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            size=size,
            wait=False,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(req)

    @property
    def hidden(self) -> bool:
        """Whether this viewport is currently hidden (not visible in the UI)."""
        return self._pb.hidden

    def _set_hidden(self, hidden: bool) -> None:
        """Update hidden state of viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            hidden=hidden,
            wait=False,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(req)

    def hide(self) -> None:
        """Hide this viewport (make it not visible in the UI)."""
        self._set_hidden(True)

    def show(self) -> None:
        """Show this viewport if it was previously hidden."""
        self._set_hidden(False)
