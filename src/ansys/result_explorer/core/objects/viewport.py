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

"""Viewport entity and metadata classes."""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, overload

from ansys.api.result_explorer.v0 import base_pb2
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict, ParseDict

from .. import models
from .base import BaseEntity
from .camera_position import CameraPosition

if TYPE_CHECKING:
    from ..client import Client
    from .solution import ChartView, MeshView, PlotView, View


_BOOL_SETTING_KEYS = {
    "explodeActive",
    "legendUseGlobalMinMax",
    "showLegend",
    "showMesh",
    "showMinMaxLabels",
    "showTable",
    "showUnsetResults",
}
_LIST_SETTING_KEYS = {
    "activeChartIndices",
    "activeCharts",
    "activeSeriesIndices",
    "activeSeries",
    "chartNames",
    "expandedGroups",
    "selectedBodies",
    "seriesNames",
    "shownBodies",
    "transparentBodies",
}
_NUMBER_SETTING_KEYS = {
    "deformationScale",
    "explodeScale",
    "legendMax",
    "legendMin",
    "selectedXAxisIndex",
    "timeFrequencySetId",
    "transparencyLevel",
}


def _setting_value_to_python(value: models.SettingValue) -> Any:
    """Convert a viewport setting value to a Python value."""
    kind = value.WhichOneof("kind")
    if kind is None:
        return None
    if kind == "string_value":
        return value.string_value
    if kind == "number_value":
        return value.number_value
    if kind == "bool_value":
        return value.bool_value
    if kind == "object_value":
        return MessageToDict(value.object_value)
    if kind == "string_list_value":
        return list(value.string_list_value.values)
    if kind == "number_list_value":
        return list(value.number_list_value.values)
    if kind == "bool_list_value":
        return list(value.bool_list_value.values)
    if kind == "object_list_value":
        return MessageToDict(value.object_list_value)
    raise ValueError(f"Unsupported viewport setting value kind: {kind}")


def _settings_to_dict(settings) -> dict[str, Any]:
    """Convert viewport settings to a Python dictionary."""
    return {
        setting.key: _normalize_setting_value(
            setting.key,
            _setting_value_to_python(setting.value) if setting.HasField("value") else None,
        )
        for setting in settings
    }


def _normalize_setting_value(key: str, value: Any) -> Any:
    """Normalize ambiguous empty setting values from the server."""
    if value not in ("", None):
        return value
    if key in _LIST_SETTING_KEYS:
        return []
    if key in _BOOL_SETTING_KEYS:
        return False
    if key in _NUMBER_SETTING_KEYS:
        return None
    return value


def _python_to_setting_value(value: Any) -> models.SettingValue:
    """Convert a Python value to a viewport setting value."""
    if isinstance(value, bool):
        return models.SettingValue(bool_value=value)
    if isinstance(value, str):
        return models.SettingValue(string_value=value)
    if isinstance(value, int | float):
        return models.SettingValue(number_value=float(value))
    if isinstance(value, struct_pb2.Struct):
        return models.SettingValue(object_value=value)
    if isinstance(value, dict):
        struct_value = struct_pb2.Struct()
        ParseDict(value, struct_value)
        return models.SettingValue(object_value=struct_value)
    if isinstance(value, list | tuple):
        values = list(value)
        if values and all(isinstance(item, bool) for item in values):
            return models.SettingValue(bool_list_value=base_pb2.BoolList(values=values))
        if values and all(isinstance(item, int | float) for item in values):
            return models.SettingValue(
                number_list_value=base_pb2.NumberList(values=[float(item) for item in values])
            )
        if values and all(isinstance(item, dict) for item in values):
            list_value = struct_pb2.ListValue()
            ParseDict(values, list_value)
            return models.SettingValue(object_list_value=list_value)
        return models.SettingValue(
            string_list_value=base_pb2.StringList(values=[str(item) for item in values])
        )
    raise TypeError(f"Unsupported viewport setting value type: {type(value).__name__}")


def _dict_to_settings(settings: dict[str, Any]) -> list[models.SettingOption]:
    """Convert a Python dictionary to viewport setting options."""
    setting_options = []
    for key, value in settings.items():
        if value is None:
            setting_options.append(models.SettingOption(key=key))
        else:
            setting_options.append(
                models.SettingOption(key=key, value=_python_to_setting_value(value))
            )
    return setting_options


def _value_or_none(settings: dict[str, Any], key: str) -> Any:
    """Return a setting value, treating empty strings as unset."""
    value = settings.get(key)
    return None if value == "" else value


def _root_setting_key(key: str) -> str:
    """Return the top-level setting key for a nested setting path."""
    return key.split(".", 1)[0]


class PbProperty:
    """Descriptor for accessing nested protobuf object properties.

    Supports dot-notation for nested keys (e.g., "cameraPosition.matrix").
    Auto-commits to server when property is set.
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
        """Set property value on nested protobuf object and apply to server."""
        self._set_nested(obj._pb_obj, self.key, value)
        if hasattr(obj, "_mark_dirty"):
            obj._mark_dirty(self.key)
        if hasattr(obj, "_apply"):
            obj._apply()

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

    def __init__(
        self,
        pb_obj: struct_pb2.Struct,
        client: Client,
        solution_id: str | None = None,
        settings=None,
        setting_options=None,
    ):
        """Initialize viewport metadata wrapper."""
        self._pb_obj = pb_obj
        self._client = client
        self._solution_id = solution_id
        self._settings = _settings_to_dict(settings) if settings is not None else {}
        self._setting_options = (
            _settings_to_dict(setting_options) if setting_options is not None else {}
        )

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
    component_name: str = PbPropertyReadOnly("componentName")
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
            return self._active_result_from_result_metadata()
        return ActiveResult(self._pb_obj["activeResult"])

    def _active_result_from_result_metadata(self) -> ActiveResult | None:
        """Build the active result from result metadata and settings."""
        if "resultMetadata" not in self._pb_obj:
            return None

        result_metadata = MessageToDict(self._pb_obj)["resultMetadata"]
        result_name = self._settings.get("result")
        result_index = 0
        result_data = None
        for index, candidate in enumerate(result_metadata):
            if result_name is None or candidate.get("name") == result_name:
                result_index = index
                result_data = candidate
                break
        if result_data is None:
            return None

        set_id = self._settings.get("timeFrequencySetId")
        component_name = self._settings.get("componentName", "Magnitude")
        component_names = result_data.get("componentNames", [])
        extremes_source = result_data
        extremes_key = "magnitudeExtremes"
        if component_name != "Magnitude":
            component_extremes = extremes_source.get("componentExtremes")
            if component_name not in component_names or component_extremes is None:
                extremes = []
            else:
                extremes = component_extremes[component_names.index(component_name)]
        else:
            extremes = extremes_source.get(extremes_key, [])

        legend_range = self._legend_range(extremes)
        legend = {"useGlobalMinMax": self._settings.get("legendUseGlobalMinMax")}
        if legend_range is not None:
            legend["range"] = legend_range

        return ActiveResult(
            {
                "resultName": result_data.get("name"),
                "type": result_data.get("type"),
                "resultIndex": result_index,
                "setId": int(set_id) if set_id is not None else None,
                "componentName": component_name,
                "dataArrayName": result_data.get("name"),
                "range": legend_range if legend_range is not None else [],
                "legend": legend,
                "extremes": extremes,
            }
        )

    @staticmethod
    def _find_result_set(result_data, set_id):
        """Find result metadata for the active set ID."""
        sets = result_data.get("sets", [])
        if set_id is None:
            return sets[0] if sets else None
        for result_set in sets:
            if int(result_set.get("setId", -1)) == int(set_id):
                return result_set
        return None

    @staticmethod
    def _legend_range(extremes) -> list[float] | None:
        """Build the scalar range from min/max extremes."""
        values = [extreme.get("value", 0.0) for extreme in extremes]
        if not values:
            return None
        return [min(values), max(values)]


class BaseChartViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to base chart viewports."""

    @property
    def series_names(self) -> list[str]:
        """List of all available series names."""
        if "activeSeries" in self._setting_options:
            return list(self._setting_options["activeSeries"])
        return [s.string_value for s in self._pb_obj["displayOptions"]["seriesNames"].values]


class ChartViewportMetadata(BaseChartViewportMetadata):
    """Read-only metadata specific to chart viewports."""

    @property
    def chart_names(self) -> list[str]:
        """List of all available chart names."""
        if "activeCharts" in self._setting_options:
            return list(self._setting_options["activeCharts"])
        if "activeCharts" in self._settings:
            return list(self._settings["activeCharts"])
        return [s.string_value for s in self._pb_obj["displayOptions"]["chartNames"].values]


class ContactTrackersViewportMetadata(BaseChartViewportMetadata):
    """Read-only metadata specific to contact trackers viewports."""

    @property
    def contact_tracker_names(self) -> list[str]:
        """List of all available contact tracker names."""
        if "activeCharts" in self._setting_options:
            return list(self._setting_options["activeCharts"])
        if "activeCharts" in self._settings:
            return list(self._settings["activeCharts"])
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


class ResultDisplayOptions:
    """Result-specific display options for plot viewports.

    These are sent to the application via the
    ``UpdateViewportRequest.settings`` field.
    Changes to properties on this object auto-commit to the application.

    Parameters
    ----------
    result : str, optional
        Result name to display.
    set_id : int, optional
        Actual set ID (from ``TimeFrequency.set_id``), not an index.
    component_name : str, optional
        Component name for the result, such as ``"Magnitude"`` or ``"X"``.
    deformation_scale : float, optional
        Deformation scale factor.
    legend_range : tuple of float, optional
        Custom legend range as ``(min, max)``.
    use_global_min_max : bool, optional
        Whether to use the global min/max for the legend range.

    Examples
    --------
    >>> from ansys.result_explorer.core import ResultDisplayOptions
    >>> opts = ResultDisplayOptions(component_name="Z", deformation_scale=3.0)

    """

    def __init__(
        self,
        result: str | None = None,
        set_id: int | None = None,
        component_name: str | None = None,
        deformation_scale: float | None = None,
        legend_range: tuple[float, float] | None = None,
        use_global_min_max: bool | None = None,
        _viewport_id: str | None = None,
        _client: Client | None = None,
        _viewport=None,
        _settings: dict[str, Any] | None = None,
        _display_options=None,
    ):
        """Initialize result display options."""
        self._viewport_id = None
        self._client = None
        self._viewport = _viewport
        self._settings = _settings
        self._display_options = _display_options
        self._dirty_keys: set[str] = set()
        self._batch_mode = False
        self._dirty = False
        self.result = result
        self.set_id = set_id
        self.component_name = component_name
        self.deformation_scale = deformation_scale
        self.legend_range = legend_range
        self.use_global_min_max = use_global_min_max
        # Set last — after this, future assignments will auto-apply
        self._viewport_id = _viewport_id
        self._client = _client

    def __setattr__(self, name: str, value) -> None:
        """Set attribute and apply to server on change."""
        object.__setattr__(self, name, value)
        if not name.startswith("_") and self._settings is not None:
            self._update_settings(name, value, mark_dirty=True)
        # Only auto-apply if attribute is not internal (_viewport_id, _client)
        # and both viewport_id and client are set
        if not name.startswith("_") and self._viewport_id is not None and self._client is not None:
            self._apply()

    def _mark_dirty(self, key: str) -> None:
        """Mark a result setting as changed."""
        self._dirty_keys.add(_root_setting_key(key))
        if self._display_options is not None:
            self._display_options._mark_dirty(key)

    def _update_settings(self, name: str, value, mark_dirty: bool = False) -> None:
        """Update the parent settings dictionary for a result option."""
        changed_keys = []
        if name == "result":
            if value is not None:
                self._settings["result"] = value
                changed_keys.append("result")
        elif name == "set_id":
            if value is not None:
                self._settings["timeFrequencySetId"] = value
                changed_keys.append("timeFrequencySetId")
        elif name == "component_name":
            if value is not None:
                self._settings["componentName"] = value
                changed_keys.append("componentName")
        elif name == "deformation_scale":
            if value is not None:
                self._settings["deformationScale"] = value
                changed_keys.append("deformationScale")
        elif name == "legend_range":
            if value is None:
                self._settings.pop("legendMin", None)
                self._settings.pop("legendMax", None)
            else:
                self._settings["legendMin"] = value[0]
                self._settings["legendMax"] = value[1]
            changed_keys.extend(["legendMin", "legendMax"])
        elif name == "use_global_min_max":
            if value is not None:
                self._settings["legendUseGlobalMinMax"] = value
                changed_keys.append("legendUseGlobalMinMax")
        if mark_dirty:
            for key in changed_keys:
                self._mark_dirty(key)

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        _viewport_id: str | None = None,
        _client: Client | None = None,
        _viewport=None,
    ) -> ResultDisplayOptions:
        """Build from viewport settings."""
        legend_min = _value_or_none(pb_obj, "legendMin")
        legend_max = _value_or_none(pb_obj, "legendMax")
        legend_range = (
            (float(legend_min), float(legend_max))
            if legend_min is not None and legend_max is not None
            else None
        )
        set_id = _value_or_none(pb_obj, "timeFrequencySetId")
        component_name = _value_or_none(pb_obj, "componentName")
        deformation_scale = _value_or_none(pb_obj, "deformationScale")

        return cls(
            result=_value_or_none(pb_obj, "result"),
            set_id=int(set_id) if set_id is not None else None,
            component_name=component_name if component_name is not None else "Magnitude",
            deformation_scale=float(deformation_scale) if deformation_scale is not None else None,
            legend_range=legend_range,
            use_global_min_max=_value_or_none(pb_obj, "legendUseGlobalMinMax"),
            _viewport_id=_viewport_id,
            _client=_client,
            _viewport=_viewport,
            _settings=pb_obj,
        )

    def _to_dict(self) -> dict[str, Any]:
        """Serialize to viewport settings dictionary."""
        settings: dict[str, Any] = {}
        if self.result is not None:
            settings["result"] = self.result
        if self.set_id is not None:
            settings["timeFrequencySetId"] = self.set_id
        if self.component_name is not None:
            settings["componentName"] = self.component_name
        if self.deformation_scale is not None:
            settings["deformationScale"] = self.deformation_scale
        if self.legend_range is not None:
            settings["legendMin"] = self.legend_range[0]
            settings["legendMax"] = self.legend_range[1]
        if self.use_global_min_max is not None:
            settings["legendUseGlobalMinMax"] = self.use_global_min_max
        return settings

    def _to_pb(self) -> list[models.SettingOption]:
        """Serialize to viewport setting options.

        Returns
        -------
        list[SettingOption]
            Setting options for ``UpdateViewportRequest.settings``.

        """
        return _dict_to_settings(self._to_dict())

    def _apply(self) -> None:
        """Apply result options to the application."""
        if self._viewport_id is None or self._client is None:
            return
        if self._batch_mode:
            object.__setattr__(self, "_dirty", True)
            return
        if self._display_options is not None:
            object.__setattr__(self, "_dirty", False)
            self._display_options._apply()
            return
        object.__setattr__(self, "_dirty", False)
        settings = self._to_dict()
        req = models.UpdateViewportRequest(
            viewport_id=self._viewport_id,
            settings=_dict_to_settings(
                {key: settings[key] for key in self._dirty_keys if key in settings}
            )
            if self._dirty_keys
            else self._to_pb(),
            wait=True,
        )
        self._dirty_keys.clear()
        updated_viewport = self._client._workspace_stub.UpdateViewport(req)
        if self._viewport is not None:
            self._viewport._pb = updated_viewport


# ---------------------------------------------------------------------------
# Viewport display options classes (read/write)
# ---------------------------------------------------------------------------


class DisplayOptions:
    """Read/write wrapper for viewport display options."""

    def __init__(
        self,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ):
        """Initialize viewport display options wrapper.

        Parameters
        ----------
        pb_obj : dict-like
            Protobuf Struct for metadata.
        client : Client
            gRPC client for server communication.
        solution_id : str, optional
            Solution ID for this viewport.
        viewport_id : str, optional
            Viewport ID for this display options instance.
        viewport : Viewport, optional
            Parent viewport reference for state updates after auto-commit.

        """
        self._pb_obj = _settings_to_dict(pb_obj) if not isinstance(pb_obj, dict) else pb_obj
        self._client = client
        self._solution_id = solution_id
        self._viewport_id = viewport_id
        self._viewport = viewport
        self._metadata = None
        self._setting_options: dict[str, Any] = {}
        self._dirty_keys: set[str] = set()
        self._batch_mode = False
        self._dirty = False

    def _mark_dirty(self, key: str) -> None:
        """Mark a setting as changed."""
        self._dirty_keys.add(_root_setting_key(key))

    def _to_pb(self) -> list[models.SettingOption]:
        """Return setting options for viewport updates.

        Returns
        -------
        list[SettingOption]
            The settings for ``UpdateViewportRequest.settings``.

        """
        settings = (
            {key: self._pb_obj[key] for key in self._dirty_keys if key in self._pb_obj}
            if self._dirty_keys
            else self._pb_obj
        )
        return _dict_to_settings(settings)

    def _apply(self) -> None:
        """Apply changes to this viewport via gRPC."""
        if self._viewport_id is None:
            raise ValueError(
                "Cannot apply display options: viewport_id is not set. "
                "Obtain options via viewport.display_options property."
            )
        if self._batch_mode:
            self._dirty = True
            return
        self._dirty = False
        req = models.UpdateViewportRequest(
            viewport_id=self._viewport_id,
            settings=self._to_pb(),
            wait=True,
        )
        self._dirty_keys.clear()
        updated_viewport = self._client._workspace_stub.UpdateViewport(req)
        if self._viewport is not None:
            self._viewport._pb = updated_viewport

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> DisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)

    def __str__(self):
        """Return display options as formatted JSON string."""
        return json.dumps(self._pb_obj, indent=2)


class ThreeDDisplayOptions(DisplayOptions):
    """Read/write display options for 3D viewports."""

    show_mesh_edges: bool = PbProperty("showMesh")
    """Whether to display mesh edges."""
    explode: bool = PbProperty("explodeActive")
    """Whether to enable explode mode."""
    explode_scale_factor: float = PbProperty("explodeScale")
    """Scale factor for explode visualization."""
    explode_direction: Literal["Radial", "X", "Y", "Z"] = PbProperty("explodeDirection")
    """Direction of explosion: ``Radial``, ``X``, ``Y``, or ``Z``."""
    expanded_groups: list[str] = PbProperty("expandedGroups")
    """List of expanded group."""
    visible_bodies: list[str] = PbProperty("shownBodies")
    """List of visible body IDs."""

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
        self._mark_dirty("cameraPosition")
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ThreeDDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class MeshDisplayOptions(ThreeDDisplayOptions):
    """Read/write display options for mesh viewports."""

    @property
    def visible_named_selection(self) -> str | None:
        """Currently visible named selection in this viewport."""
        return self._pb_obj["shownNamedSelectionId"]

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
            self._pb_obj["shownNamedSelectionId"] = None
            self._mark_dirty("shownNamedSelectionId")
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

        self._pb_obj["shownNamedSelectionId"] = ns.id
        self._mark_dirty("shownNamedSelectionId")
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> MeshDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class PlotDisplayOptions(ThreeDDisplayOptions):
    """Read/write display options for plot viewports.

    The ``result_options`` field holds result-specific options
    such as the active result, component, and deformation scale.
    """

    show_min_max_labels: bool = PbProperty("showMinMaxLabels")
    """Whether to display min/max labels on the plot."""

    def __init__(
        self,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
        result_options: ResultDisplayOptions | None = None,
    ):
        """Initialize plot viewport display options."""
        super().__init__(pb_obj, client, solution_id, viewport_id, viewport)
        self._result_options = result_options
        if self._result_options is not None:
            self._result_options._settings = self._pb_obj
            self._result_options._display_options = self

    @property
    def result_options(self) -> ResultDisplayOptions:
        """Result-specific display options wrapper."""
        if self._result_options is None:
            self._result_options = ResultDisplayOptions._from_pb(
                self._pb_obj,
                _viewport_id=self._viewport_id,
                _client=self._client,
                _viewport=self._viewport,
            )
        return self._result_options

    @result_options.setter
    def result_options(self, value: ResultDisplayOptions) -> None:
        """Set result options and apply to server."""
        value._viewport_id = self._viewport_id
        value._client = self._client
        value._viewport = self._viewport
        value._settings = self._pb_obj
        value._display_options = self
        for name in (
            "result",
            "set_id",
            "component_name",
            "deformation_scale",
            "legend_range",
            "use_global_min_max",
        ):
            value._update_settings(name, getattr(value, name), mark_dirty=True)
        self._result_options = value
        if self._viewport_id is not None and self._client is not None:
            self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> PlotDisplayOptions:
        """Build from a metadata Struct, populating result_options."""
        settings = _settings_to_dict(pb_obj) if not isinstance(pb_obj, dict) else pb_obj
        return cls(
            settings,
            client,
            solution_id,
            viewport_id,
            viewport,
            result_options=ResultDisplayOptions._from_pb(
                settings,
                _viewport_id=viewport_id,
                _client=client,
                _viewport=viewport,
            ),
        )


class BaseChartDisplayOptions(DisplayOptions):
    """Read/write display options for base chart viewports."""

    show_legend: bool = PbProperty("showLegend")
    """Whether to display the legend."""
    show_table: bool = PbProperty("showTable")
    """Whether to display the data table."""

    @property
    def split_direction(self) -> Literal["horizontal", "vertical"]:
        """Direction to split chart and table: ``horizontal`` or ``vertical``."""
        value = self._pb_obj.get("tablePosition", self._pb_obj.get("splitDirection"))
        if value is None:
            return "vertical"
        return value

    @split_direction.setter
    def split_direction(self, value: Literal["horizontal", "vertical"]) -> None:
        """Set the chart table split direction."""
        self._pb_obj["tablePosition"] = value
        self._mark_dirty("tablePosition")
        self._apply()

    @property
    def _display_options_metadata(self):
        """Nested display options metadata, when available."""
        if self._metadata is None or "displayOptions" not in self._metadata:
            return {}
        return self._metadata["displayOptions"]

    @property
    def series_names(self) -> list[str]:
        """List of all available series names."""
        if "activeSeries" in self._setting_options:
            return list(self._setting_options["activeSeries"])
        if "seriesNames" in self._pb_obj:
            return list(self._pb_obj["seriesNames"])
        return [s.string_value for s in self._display_options_metadata["seriesNames"].values]

    @property
    def active_series(self) -> list[str]:
        """List of currently active series."""
        if "activeSeries" in self._pb_obj:
            return list(self._pb_obj["activeSeries"])
        indices = self._pb_obj.get("activeSeriesIndices")
        if indices is None:
            indices = self._display_options_metadata["activeSeriesIndices"]
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
        self._pb_obj["activeSeries"] = names
        self._mark_dirty("activeSeries")
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> BaseChartDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class ChartDisplayOptions(BaseChartDisplayOptions):
    """Read/write display options for chart viewports."""

    @property
    def chart_names(self) -> list[str]:
        """List of all available chart names."""
        if "activeCharts" in self._setting_options:
            return list(self._setting_options["activeCharts"])
        if "activeCharts" in self._pb_obj:
            return list(self._pb_obj["activeCharts"])
        if "chartNames" in self._pb_obj:
            return list(self._pb_obj["chartNames"])
        return [s.string_value for s in self._display_options_metadata["chartNames"].values]

    @property
    def active_charts(self) -> list[str]:
        """List of currently active charts."""
        if "activeCharts" in self._pb_obj:
            return list(self._pb_obj["activeCharts"])
        indices = self._pb_obj.get("activeChartIndices")
        if indices is None:
            indices = self._display_options_metadata["activeChartIndices"]
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
        self._pb_obj["activeCharts"] = names
        self._mark_dirty("activeCharts")
        self._apply()

    @property
    def selected_x_axis(self) -> str:
        """Name of the currently selected x-axis series."""
        if "xAxisSeries" in self._pb_obj:
            return self._pb_obj["xAxisSeries"]
        idx = self._pb_obj.get("selectedXAxisIndex")
        if idx is None:
            idx = self._display_options_metadata["selectedXAxisIndex"]
        idx = int(idx)
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
        self._pb_obj["xAxisSeries"] = name
        self._mark_dirty("xAxisSeries")
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ChartDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class ContactTrackersDisplayOptions(BaseChartDisplayOptions):
    """Read/write display options for contact trackers viewports."""

    @property
    def contact_tracker_names(self) -> list[str]:
        """List of all available contact tracker names."""
        if "activeCharts" in self._setting_options:
            return list(self._setting_options["activeCharts"])
        if "activeCharts" in self._pb_obj:
            return list(self._pb_obj["activeCharts"])
        if "chartNames" in self._pb_obj:
            return list(self._pb_obj["chartNames"])
        return [s.string_value for s in self._display_options_metadata["chartNames"].values]

    @property
    def active_contact_trackers(self) -> list[str]:
        """List of currently active contact trackers."""
        if "activeCharts" in self._pb_obj:
            return list(self._pb_obj["activeCharts"])
        indices = self._pb_obj.get("activeChartIndices")
        if indices is None:
            indices = self._display_options_metadata["activeChartIndices"]
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
        self._pb_obj["activeCharts"] = names
        self._mark_dirty("activeCharts")
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ContactTrackersDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class ConvergenceTrackersDisplayOptions(DisplayOptions):
    """Read/write display options for convergence trackers viewports."""

    selected_tracker_name: str = PbProperty("tracker")
    """Name of the currently selected convergence tracker."""

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ConvergenceTrackersDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class LogsDisplayOptions(DisplayOptions):
    """Read/write display options for logs viewports."""

    """Path to the currently displayed log file."""

    @property
    def log_path(self) -> str:
        """Path to the currently displayed log file."""
        return self._pb_obj.get("logFile", self._pb_obj.get("currentLogPath"))

    @log_path.setter
    def log_path(self, value: str) -> None:
        """Set the currently displayed log file."""
        self._pb_obj["logFile"] = value
        self._mark_dirty("logFile")
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> LogsDisplayOptions:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


# ---------------------------------------------------------------------------
# Viewport entity
# ---------------------------------------------------------------------------


class Viewport[TDisplayOptions: DisplayOptions](BaseEntity[models.Viewport]):
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
        settings = self._pb.settings
        setting_options = self._pb.setting_options

        if view is None:
            return ViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            return PlotViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            return ChartViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            return MeshViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            return ConvergenceTrackersViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            return ContactTrackersViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )
        elif view.type == models.ViewType.VIEW_TYPE_LOGS:
            return LogsViewportMetadata(
                pb_obj, self._client, self.solution_id, settings, setting_options
            )

        return ViewportMetadata(pb_obj, self._client, self.solution_id, settings, setting_options)

    @property
    def display_options(self) -> TDisplayOptions:
        """Read/write viewport display options."""
        view = self._resolve_view()
        pb_obj = self._pb.settings

        if view is None:
            opts = DisplayOptions._from_pb(pb_obj, self._client, self.solution_id, self.id, self)
            opts._metadata = MessageToDict(self._pb.metadata)
            opts._setting_options = _settings_to_dict(self._pb.setting_options)
            return opts

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            opts = PlotDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id, self.id, self
            )
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            opts = ChartDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id, self.id, self
            )
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            opts = MeshDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id, self.id, self
            )
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            opts = ConvergenceTrackersDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id, self.id, self
            )
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            opts = ContactTrackersDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id, self.id, self
            )
        elif view.type == models.ViewType.VIEW_TYPE_LOGS:
            opts = LogsDisplayOptions._from_pb(
                pb_obj, self._client, self.solution_id, self.id, self
            )
        else:
            opts = DisplayOptions._from_pb(pb_obj, self._client, self.solution_id, self.id, self)

        opts._metadata = MessageToDict(self._pb.metadata)
        opts._setting_options = _settings_to_dict(self._pb.setting_options)
        return opts

    @property
    def setting_options(self) -> dict[str, Any]:
        """Available values for viewport settings that support them."""
        return _settings_to_dict(self._pb.setting_options)

    @contextmanager
    def update_display_options(self) -> Generator[TDisplayOptions, None, None]:
        """Batch display options updates in a single server call.

        Suppresses auto-commit during the block and flushes all
        changes on exit.

        Yields
        ------
        DisplayOptions
            The display options object to modify.

        Examples
        --------
        >>> with viewport.update_display_options() as opts:
        ...     opts.show_mesh_edges = True
        ...     opts.result_options.deformation_scale = 2.5

        """
        opts = self.display_options
        opts._batch_mode = True
        result_opts = opts._result_options if isinstance(opts, PlotDisplayOptions) else None
        if result_opts is not None:
            object.__setattr__(result_opts, "_batch_mode", True)
        try:
            yield opts
        finally:
            opts._batch_mode = False
            result_opts = opts._result_options if isinstance(opts, PlotDisplayOptions) else None
            if result_opts is not None:
                object.__setattr__(result_opts, "_batch_mode", False)
            if opts._dirty:
                opts._apply()
            if result_opts is not None and result_opts._dirty:
                result_opts._apply()

    @property
    def size(self) -> float:
        """Size of the viewport as a percentage of its parent."""
        return self._pb.size

    @overload
    def set_view(self, view: PlotView, wait: bool = ...) -> Viewport[PlotDisplayOptions]: ...
    @overload
    def set_view(self, view: ChartView, wait: bool = ...) -> Viewport[ChartDisplayOptions]: ...
    @overload
    def set_view(self, view: MeshView, wait: bool = ...) -> Viewport[MeshDisplayOptions]: ...
    @overload
    def set_view(self, view: View, wait: bool = ...) -> Viewport[DisplayOptions]: ...
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

    def save_snapshot(
        self, file_path: str | Path, settings: models.SnapshotSettings | None = None
    ) -> None:
        """Take a snapshot of this viewport and save it to PNG.

        Parameters
        ----------
        file_path : str | Path
            Path to save the PNG image.
        settings : SnapshotSettings, optional
            Snapshot settings to control what elements appear in the image
            (timestamp, logo, legend, solution name, etc.). If None, uses server defaults.

        """
        snapshot_data = self.take_snapshot(settings)

        # make sure the directory exists
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # if the extension is not .png, add it
        if file_path.suffix.lower() != ".png":
            file_path = file_path.with_suffix(".png")

        with open(file_path, "wb") as f:
            f.write(snapshot_data)

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
