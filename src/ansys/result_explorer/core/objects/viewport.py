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

from google.protobuf.json_format import MessageToDict

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
    """Wrapper for viewport metadata."""

    def __init__(self, pb_obj: models.Viewport, client: Client, solution_id: str | None = None):
        """Initialize viewport metadata wrapper."""
        self._pb_obj = pb_obj
        self._client = client
        self._solution_id = solution_id

    def to_pb(self) -> models.Viewport:
        """Convert back for gRPC calls."""
        return self._pb_obj

    def __str__(self):
        """Return metadata as formatted JSON string."""
        # print as json-like string
        json_str = json.dumps(MessageToDict(self._pb_obj), indent=2)
        return json_str


class ThreeDViewportMetadata(ViewportMetadata):
    """Metadata specific to 3D viewports."""

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


class MeshViewportMetadata(ThreeDViewportMetadata):
    """Metadata specific to mesh viewports."""

    @property
    def visible_named_selection(self) -> str | None:
        """Currently visible named selection in this viewport."""
        return self._pb_obj["shownNamedSelection"]

    @visible_named_selection.setter
    def visible_named_selection(self, value: str | models.NamedSelection = None) -> None:
        """Set the visible named selection in this viewport.

        Parameters
        ----------
        value : str or NamedSelection, optional
            The named selection to show. Can be specified by id, name or
            by passing a NamedSelection object. If None, no named selection will be shown.

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


class LegendSettings:
    """Legend display settings for a plot result.

    Controls colors, range, and discretization.
    """

    use_global_min_max: bool = PbProperty("useGlobalMinMax")
    range: list[float] = PbProperty("range")

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
            value=pb_obj["value"],
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
    """Active result currently displayed in a plot viewport."""

    result_name: str = PbProperty("resultName")
    time_set_index: int = PbProperty("timeSetIndex")
    component_index: int = PbProperty("componentIndex")

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
    def extremes(self) -> list[ResultExtreme]:
        """Min/max extremes of the result."""
        if "extremes" not in self._pb_obj:
            return []
        return [ResultExtreme._from_pb(e) for e in self._pb_obj["extremes"] if "value" in e]


class PlotViewportMetadata(ThreeDViewportMetadata):
    """Metadata specific to plot viewports."""

    show_min_max_labels: bool = PbProperty("showMinMaxLabels")
    deformation_scale: float = PbProperty("deformationScale")

    @property
    def active_result(self) -> ActiveResult | None:
        """Active result currently displayed, or None if not set."""
        if "activeResult" not in self._pb_obj:
            return None
        return ActiveResult(self._pb_obj["activeResult"])


class BaseChartViewportMetadata(ViewportMetadata):
    """Metadata specific to base chart viewports."""

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


class ChartViewportMetadata(BaseChartViewportMetadata):
    """Metadata specific to chart viewports."""

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


class ContactTrackersViewportMetadata(BaseChartViewportMetadata):
    """Metadata specific to contact trackers viewports."""

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


class ConvergenceTrackersViewportMetadata(ViewportMetadata):
    """Metadata specific to convergence trackers viewports."""

    selected_tracker_name: str = PbProperty("selectedTrackerName")


class LogsViewportMetadata(ViewportMetadata):
    """Metadata specific to logs viewports."""

    log_path: str = PbProperty("currentLogPath")


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

    @property
    def metadata(self) -> ViewportMetadata:
        """Access viewport metadata."""
        view = self.view
        metadata = self._pb.metadata

        if view is None:
            return ViewportMetadata(metadata, self._client, self.solution_id)

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            return PlotViewportMetadata(metadata, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            return ChartViewportMetadata(metadata, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            return MeshViewportMetadata(metadata, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            return ConvergenceTrackersViewportMetadata(metadata, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            return ContactTrackersViewportMetadata(metadata, self._client, self.solution_id)
        elif view.type == models.ViewType.VIEW_TYPE_LOGS:
            return LogsViewportMetadata(metadata, self._client, self.solution_id)

        return ViewportMetadata(metadata, self._client, self.solution_id)

    @property
    def size(self) -> float:
        """Size of the viewport as a percentage of its parent."""
        return self._pb.size

    @property
    def view(self) -> View | None:
        """Get the assigned view, if any."""
        # todo: we could cache this

        if self.view_id and self.solution_id:
            solution = self._client.get_solution(self.solution_id)
            view = next((v for v in solution.views if v.id == self.view_id), None)
            return view
        return None

    def set_view(self, view: View, wait: bool = True) -> Viewport:
        """Assign a view to this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            solution_id=view.solution.id,
            view_id=view.id,
            wait=wait,
        )
        updated_pb = self._client._workspace_stub.UpdateViewport(req)
        self._pb = updated_pb
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

    def set_metadata(self, metadata: ViewportMetadata) -> None:
        """Update metadata for this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            metadata=metadata.to_pb(),
            wait=True,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(req)

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
