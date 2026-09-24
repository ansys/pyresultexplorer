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

import dataclasses
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


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------


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


class _SettingValueMixin:
    """Adds ``.value``/``.options`` to a value that stays usable as its own type."""

    _value: Any
    _options: list[Any] | None

    @property
    def value(self) -> Any:
        """Current value of the setting."""
        return self._value

    @property
    def options(self) -> list[Any] | None:
        """Available values for the setting, or None if unconstrained."""
        return self._options

    def __repr__(self) -> str:
        if self._options is None:
            return repr(self._value)
        return f"{self._value!r} (options: {self._options!r})"

    def __str__(self) -> str:
        if self._options is None:
            return str(self._value)
        return f"{self._value} (options: {self._options})"


class _OpaqueSettingValue:
    """Value/options pair for setting values whose type cannot be subclassed."""

    def __init__(self, value: Any, options: list[Any] | None):
        self._value = value
        self._options = options

    @property
    def value(self) -> Any:
        """Current value of the setting."""
        return self._value

    @property
    def options(self) -> list[Any] | None:
        """Available values for the setting, or None if unconstrained."""
        return self._options

    def __bool__(self) -> bool:
        return bool(self._value)

    def __eq__(self, other: object) -> bool:
        return self._value == (other.value if isinstance(other, _OpaqueSettingValue) else other)

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        if self._options is None:
            return repr(self._value)
        return f"{self._value!r} (options: {self._options!r})"

    def __str__(self) -> str:
        if self._options is None:
            return str(self._value)
        return f"{self._value} (options: {self._options})"


def _wrap_setting_value(value: Any, options: list[Any] | None) -> Any:
    """Wrap a raw setting value so it also exposes ``.value``/``.options``.

    The result stays usable as the original type wherever possible (for
    example, a wrapped string still supports string methods and equality).
    ``bool`` can't be subclassed, so it gets a small dedicated wrapper
    instead. An unset (``None``) value is returned as-is so ``is None``
    checks on optional settings keep working.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return _OpaqueSettingValue(value, options)
    try:
        # Mixin listed first so its __repr__/__str__ take priority over the
        # base type's (built-in types like str/int define their own).
        cls = type(f"{type(value).__name__}Setting", (_SettingValueMixin, type(value)), {})
        try:
            wrapped = cls(value)
        except TypeError:
            wrapped = object.__new__(cls)
            wrapped.__dict__.update(getattr(value, "__dict__", {}))
    except TypeError:
        return _OpaqueSettingValue(value, options)
    wrapped._value = value
    wrapped._options = options
    return wrapped


def _unwrap_setting_value(value: Any) -> Any:
    """Return the raw value from a wrapped setting, passing through otherwise."""
    if isinstance(value, _SettingValueMixin | _OpaqueSettingValue):
        return value.value
    return value


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
        value = self._get_nested(obj._pb_obj, self.key)
        return obj._wrap(self.key, value)

    def __set__(self, obj, value):
        """Set property value on nested protobuf object and apply to server."""
        self._set_nested(obj._pb_obj, self.key, _unwrap_setting_value(value))
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


# ---------------------------------------------------------------------------
# Viewport metadata classes (readonly)
# ---------------------------------------------------------------------------


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


@dataclass(frozen=True)
class ResultExtremes:
    """Read-only min/max extremes."""

    min: ResultExtreme | None
    """Minimum extreme of the result set."""
    max: ResultExtreme | None
    """Maximum extreme of the result set."""

    @classmethod
    def _from_pb(cls, pb_obj) -> ResultExtremes:
        """Build from a protobuf struct object."""
        return cls(
            min=ResultExtreme._from_pb(pb_obj[0]) if len(pb_obj) > 0 else None,
            max=ResultExtreme._from_pb(pb_obj[1]) if len(pb_obj) > 1 else None,
        )


@dataclass(frozen=True)
class ActiveResult:
    """Read-only metadata for the active result in a plot viewport."""

    result_name: str
    """Name of the result."""

    component_name: str
    """Name of the component."""

    id: str
    """Identifier for the result set."""

    set_id: int
    """Set number."""

    unit: str
    """Result unit."""

    time_frequency: float
    """Time or frequency associated with the result set."""

    min: ResultExtreme
    """Minimum extreme of the result set."""

    max: ResultExtreme
    """Maximum extreme of the result set."""

    def __str__(self) -> str:
        """Return a string representation of the active result."""
        s = "\n"
        s += json.dumps(dataclasses.asdict(self), indent=2)
        s += "\n"
        return s


@dataclass(frozen=True)
class ResultSetMetadata:
    """Read-only result set metadata for a plot view."""

    id: str
    """Identifier for the result set."""

    set_id: int
    """Set number."""

    time_frequency: float
    """Time or frequency associated with the result set."""

    component_extremes: list[ResultExtremes]
    """Min/max extremes for each component in the result set."""

    magnitude_extremes: list[ResultExtremes]
    """Min/max extremes for the magnitude of the result set."""

    @classmethod
    def _from_pb(cls, pb_obj) -> ResultSetMetadata:
        """Build from a protobuf struct object."""
        return cls(
            id=pb_obj["id"],
            set_id=int(pb_obj["setId"]),
            time_frequency=float(pb_obj["timeFrequency"]),
            component_extremes=[ResultExtremes._from_pb(e) for e in pb_obj["componentExtremes"]],
            magnitude_extremes=ResultExtremes._from_pb(pb_obj["magnitudeExtremes"]),
        )

    def __str__(self) -> str:
        """Return a string representation of the result set metadata."""
        s = "\n"
        s += json.dumps(dataclasses.asdict(self), indent=2)
        s += "\n"
        return s

    def __repr__(self) -> str:
        """Return a string representation of the result set metadata."""
        return self.__str__()


@dataclass(frozen=True)
class ResultMetadata:
    """Read-only result metadata for a plot view."""

    name: str
    """Result name."""
    type: str
    """Result type."""
    unit: str
    """Result unit."""
    num_components: int
    """Number of components in the result."""
    component_names: list[str]
    """Names of the components in the result."""
    sets: list[ResultSetMetadata]
    """List of result sets associated with the result."""
    global_component_extremes: list[ResultExtremes]
    """Global (over all result sets) min/max extremes for each component in the result."""
    global_magnitude_extremes: list[ResultExtremes]
    """Global (over all result sets) min/max extremes for the magnitude of the result."""

    @classmethod
    def _from_pb(cls, pb_obj) -> ResultMetadata:
        """Build from a protobuf struct object."""
        return cls(
            name=pb_obj["name"],
            type=pb_obj["type"],
            unit=pb_obj["unit"],
            num_components=int(pb_obj["components"]),
            component_names=list(pb_obj["componentNames"]),
            sets=[ResultSetMetadata._from_pb(s) for s in pb_obj["sets"]],
            global_component_extremes=[
                ResultExtremes._from_pb(e) for e in pb_obj["componentExtremes"]
            ],
            global_magnitude_extremes=ResultExtremes._from_pb(pb_obj["magnitudeExtremes"]),
        )

    def __str__(self) -> str:
        """Return a string representation of the result metadata."""
        s = "\n"
        s += json.dumps(dataclasses.asdict(self), indent=2)
        s += "\n"
        return s

    def __repr__(self) -> str:
        """Return a string representation of the result metadata."""
        return self.__str__()


class PlotViewportMetadata(ViewportMetadata):
    """Read-only metadata specific to plot viewports."""

    @property
    def results(self) -> list[ResultMetadata]:
        """List of results metadata available in this plot view."""
        if "resultMetadata" not in self._pb_obj:
            return []
        return [ResultMetadata._from_pb(r) for r in self._pb_obj["resultMetadata"]]

    @property
    def available_results(self) -> list[str]:
        """List of available result names in this plot view."""
        if "resultMetadata" not in self._pb_obj:
            return []
        return [r["name"] for r in self._pb_obj["resultMetadata"]]

    @property
    def active_result(self) -> ActiveResult | None:
        """Active result currently displayed, or None if not set."""
        return self._active_result_from_results_metadata()

    def _active_result_from_results_metadata(self) -> ActiveResult | None:
        """Build the active result from result metadata and settings."""
        if "resultMetadata" not in self._pb_obj:
            return None

        results_metadata = self.results
        result_name = self._settings.get("result")
        result_data: ResultMetadata | None = None
        for _, candidate in enumerate(results_metadata):
            if result_name is None or candidate.name == result_name:
                result_data = candidate
                break
        if result_data is None:
            return None

        set_id = self._settings.get("timeFrequencySetId")
        if set_id is None:
            raise ValueError("timeFrequencySetId is not set in viewport settings.")
        set_id = int(set_id)

        component_name = self._settings.get("componentName", "Magnitude")
        # find result set
        result_set = next((s for s in result_data.sets if s.set_id == set_id), None)
        if result_set is None:
            raise ValueError(f"Result set with ID {set_id} not found in result metadata.")

        if component_name.lower() == "magnitude":
            extremes = result_set.magnitude_extremes
        else:
            component_index = next(
                (i for i, name in enumerate(result_data.component_names) if name == component_name),
                None,
            )
            if component_index is None:
                raise ValueError(f"Component '{component_name}' not found in result metadata.")

            extremes = result_set.component_extremes[component_index]

        return ActiveResult(
            result_name=result_data.name,
            id=result_set.id,
            set_id=set_id,
            unit=result_data.unit,
            time_frequency=result_set.time_frequency,
            component_name=component_name,
            min=extremes.min,
            max=extremes.max,
        )


# ---------------------------------------------------------------------------
# Viewport settings classes (read/write)
# ---------------------------------------------------------------------------


class ViewportSettings:
    """Manages editable viewport settings."""

    def __init__(
        self,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ):
        """Initialize viewport settings wrapper.

        Parameters
        ----------
        pb_obj : dict-like
            Protobuf Struct for settings.
        client : Client
            gRPC client for server communication.
        solution_id : str, optional
            Solution ID for this viewport.
        viewport_id : str, optional
            Viewport ID for this settings instance.
        viewport : Viewport, optional
            Parent viewport reference for state updates after auto-commit.

        """
        self._pb_obj = _settings_to_dict(pb_obj) if not isinstance(pb_obj, dict) else pb_obj
        self._client = client
        self._solution_id = solution_id
        self._viewport_id = viewport_id
        self._viewport = viewport
        self._setting_options: dict[str, Any] = {}
        self._batch_mode = False

    def _wrap(self, key: str, value: Any) -> Any:
        """Wrap a raw value together with its available options, if known."""
        return _wrap_setting_value(value, self._setting_options.get(_root_setting_key(key)))

    def _to_pb(self) -> list[models.SettingOption]:
        """Return setting options for viewport updates.

        Returns
        -------
        list[SettingOption]
            The settings for ``UpdateViewportRequest.settings``.

        """
        settings = self._pb_obj
        return _dict_to_settings(settings)

    def _apply(self) -> None:
        """Apply changes to this viewport via gRPC."""
        if self._viewport_id is None:
            raise ValueError(
                "Cannot apply settings: viewport_id is not set. "
                "Obtain settings via viewport.settings."
            )
        if self._batch_mode:
            return
        req = models.UpdateViewportRequest(
            viewport_id=self._viewport_id,
            settings=self._to_pb(),
            wait=True,
        )
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
    ) -> ViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)

    def __str__(self):
        """Return viewport settings as formatted JSON string."""
        return json.dumps(self._pb_obj, indent=2)


class ThreeDViewportSettings(ViewportSettings):
    """Manages editable settings for 3D viewports."""

    show_mesh_edges: bool = PbProperty("showMesh")
    """Whether to display the mesh edges."""
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
    def camera_position(self) -> Any:
        """Current camera position, or None if not set."""
        if "cameraPosition" not in self._pb_obj:
            return self._wrap("cameraPosition", None)
        raw = self._pb_obj["cameraPosition"]
        return self._wrap("cameraPosition", CameraPosition(list(raw["matrix"])))

    @camera_position.setter
    def camera_position(self, value: CameraPosition) -> None:
        """Set the camera position."""
        value = _unwrap_setting_value(value)
        self._pb_obj["cameraPosition"] = {"matrix": value.matrix}
        self._apply()

    @property
    def left_click_modes(self) -> list[str]:
        """Available left-click interaction modes.

        TODO: no writable "active mode" setting exists yet.
        """
        return self._setting_options.get("leftClickMode", [])

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ThreeDViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class MeshViewportSettings(ThreeDViewportSettings):
    """Manages editable settings for mesh viewports."""

    @property
    def visible_named_selection(self) -> Any:
        """Currently visible named selection in this viewport."""
        return self._wrap("shownNamedSelectionId", self._pb_obj["shownNamedSelectionId"])

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
        value = _unwrap_setting_value(value)
        if value is None:
            self._pb_obj["shownNamedSelectionId"] = ""
            self._apply()
            return

        solution = self._client.get_solution(self._solution_id)

        ns = None
        if isinstance(value, models.NamedSelection):
            ns = value

        if ns is None:
            ns = next((x for x in solution.named_selections if x.id == value), None)

        if ns is None:
            ns = next((x for x in solution.named_selections if x.name == value), None)

        if ns is None:
            raise ValueError(f"No named selection with id or name '{value}' found in solution.")

        self._pb_obj["shownNamedSelectionId"] = ns.id
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> MeshViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class PlotViewportSettings(ThreeDViewportSettings):
    """Manages editable settings for plot viewports."""

    show_min_max_labels: bool = PbProperty("showMinMaxLabels")
    """Whether to display min/max labels on the plot."""

    @property
    def result(self) -> Any:
        """Name of the result currently displayed."""
        return self._wrap("result", _value_or_none(self._pb_obj, "result"))

    @result.setter
    def result(self, value: str | None) -> None:
        """Set the result to display."""
        value = _unwrap_setting_value(value)
        if value is not None:
            self._pb_obj["result"] = value
        self._apply()

    @property
    def set_id(self) -> Any:
        """Actual time/frequency set ID (not an index)."""
        value = _value_or_none(self._pb_obj, "timeFrequencySetId")
        return self._wrap("timeFrequencySetId", int(value) if value is not None else None)

    @set_id.setter
    def set_id(self, value: int | None) -> None:
        """Set the active time/frequency set ID."""
        value = _unwrap_setting_value(value)
        if value is not None:
            self._pb_obj["timeFrequencySetId"] = value
        self._apply()

    @property
    def component_name(self) -> Any:
        """Component name for the active result, such as ``"X"`` or ``"Magnitude"``."""
        value = _value_or_none(self._pb_obj, "componentName")
        return self._wrap("componentName", value if value is not None else "Magnitude")

    @component_name.setter
    def component_name(self, value: str) -> None:
        """Set the active result component."""
        value = _unwrap_setting_value(value)
        if value is not None:
            self._pb_obj["componentName"] = value
        self._apply()

    @property
    def deformation_scale(self) -> Any:
        """Deformation scale factor."""
        value = _value_or_none(self._pb_obj, "deformationScale")
        return self._wrap("deformationScale", float(value) if value is not None else None)

    @deformation_scale.setter
    def deformation_scale(self, value: float | None) -> None:
        """Set the deformation scale factor."""
        value = _unwrap_setting_value(value)
        if value is not None:
            self._pb_obj["deformationScale"] = value
        self._apply()

    @property
    def use_global_min_max(self) -> Any:
        """Whether to use the global min/max for the legend range."""
        value = _value_or_none(self._pb_obj, "legendUseGlobalMinMax")
        return self._wrap("legendUseGlobalMinMax", value)

    @use_global_min_max.setter
    def use_global_min_max(self, value: bool | None) -> None:
        """Set whether to use the global min/max for the legend range."""
        value = _unwrap_setting_value(value)
        if value is not None:
            self._pb_obj["legendUseGlobalMinMax"] = value
        self._apply()

    @property
    def legend_range(self) -> Any:
        """Custom legend range as ``(min, max)``, or None for auto-range."""
        legend_min = _value_or_none(self._pb_obj, "legendMin")
        legend_max = _value_or_none(self._pb_obj, "legendMax")
        value = (
            (float(legend_min), float(legend_max))
            if legend_min is not None and legend_max is not None
            else None
        )
        return self._wrap("legendMin", value)

    @legend_range.setter
    def legend_range(self, value: tuple[float, float] | None) -> None:
        """Set the legend range, or None to restore auto-range."""
        value = _unwrap_setting_value(value)
        if value is None:
            self._pb_obj.pop("legendMin", None)
            self._pb_obj.pop("legendMax", None)
        else:
            self._pb_obj["legendMin"] = value[0]
            self._pb_obj["legendMax"] = value[1]
        self._apply()

    @property
    def color_maps(self) -> list[str]:
        """Available legend color maps.

        TODO: no writable color-map setting exists yet.
        """
        return self._setting_options.get("legendColorMap", [])

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> PlotViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class BaseChartViewportSettings(ViewportSettings):
    """Manages editable settings for chart viewports."""

    show_legend: bool = PbProperty("showLegend")
    """Whether to display the legend."""
    show_table: bool = PbProperty("showTable")
    """Whether to display the data table."""

    @property
    def split_direction(self) -> Any:
        """Direction to split chart and table: ``horizontal`` or ``vertical``."""
        value = self._pb_obj.get("tablePosition", self._pb_obj.get("splitDirection"))
        if value is None:
            value = "vertical"
        return self._wrap("tablePosition", value)

    @split_direction.setter
    def split_direction(self, value: Literal["horizontal", "vertical"]) -> None:
        """Set the chart table split direction."""
        self._pb_obj["tablePosition"] = _unwrap_setting_value(value)
        self._apply()

    @property
    def series_names(self) -> list[str]:
        """List of all available series names."""
        if "activeSeries" in self._setting_options:
            return list(self._setting_options["activeSeries"])
        if "seriesNames" in self._pb_obj:
            return list(self._pb_obj["seriesNames"])
        return []

    @property
    def active_series(self) -> Any:
        """List of currently active series."""
        value = list(self._pb_obj["activeSeries"]) if "activeSeries" in self._pb_obj else []
        return _wrap_setting_value(value, self.series_names)

    @active_series.setter
    def active_series(self, names: list[str]) -> None:
        """Set the active series.

        Parameters
        ----------
        names : list[str]
            List of series names to make active.

        """
        names = _unwrap_setting_value(names)
        for name in names:
            if name not in self.series_names:
                raise ValueError(f"Invalid series name: {name}")
        self._pb_obj["activeSeries"] = names
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> BaseChartViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class ChartViewportSettings(BaseChartViewportSettings):
    """Read/write settings for chart viewports."""

    show_chart: bool = PbProperty("showChart")
    """Whether to display the chart."""

    @property
    def chart_names(self) -> list[str]:
        """List of all available chart names."""
        if "activeCharts" in self._setting_options:
            return list(self._setting_options["activeCharts"])
        if "activeCharts" in self._pb_obj:
            return list(self._pb_obj["activeCharts"])
        if "chartNames" in self._pb_obj:
            return list(self._pb_obj["chartNames"])
        return []

    @property
    def selected_x_axis(self) -> Any:
        """Name of the currently selected x-axis series."""
        value = self._pb_obj.get("xAxisSeries", "")
        return _wrap_setting_value(value, self.series_names)

    @selected_x_axis.setter
    def selected_x_axis(self, name: str) -> None:
        """Set the x-axis series.

        Parameters
        ----------
        name : str
            Name of the series to use as the x-axis.

        """
        name = _unwrap_setting_value(name)
        if name not in self.series_names:
            raise ValueError(f"Invalid x-axis name: {name}")
        self._pb_obj["xAxisSeries"] = name
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ChartViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class ContactTrackersViewportSettings(BaseChartViewportSettings):
    """Read/write settings for contact trackers viewports."""

    show_chart: bool = PbProperty("showChart")
    """Whether to display the chart."""
    selection_mode: str = PbProperty("chartSelectionMode")
    """Current contact tracker selection mode."""

    @property
    def contact_tracker_names(self) -> list[str]:
        """List of all available contact tracker names."""
        if "activeCharts" in self._setting_options:
            return list(self._setting_options["activeCharts"])
        if "activeCharts" in self._pb_obj:
            return list(self._pb_obj["activeCharts"])
        if "chartNames" in self._pb_obj:
            return list(self._pb_obj["chartNames"])
        return []

    @property
    def active_contact_trackers(self) -> Any:
        """List of currently active contact trackers."""
        value = list(self._pb_obj["activeCharts"]) if "activeCharts" in self._pb_obj else []
        return _wrap_setting_value(value, self.contact_tracker_names)

    @active_contact_trackers.setter
    def active_contact_trackers(self, names: list[str]) -> None:
        """Set the active contact trackers.

        Parameters
        ----------
        names : list[str]
            List of contact tracker names to make active.

        """
        names = _unwrap_setting_value(names)
        for name in names:
            if name not in self.contact_tracker_names:
                raise ValueError(f"Invalid contact tracker name: {name}")
        self._pb_obj["activeCharts"] = names
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> ContactTrackersViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class ConvergenceTrackersViewportSettings(ViewportSettings):
    """Read/write settings for convergence trackers viewports."""

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
    ) -> ConvergenceTrackersViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


class LogsViewportSettings(ViewportSettings):
    """Read/write settings for logs viewports."""

    @property
    def log_path(self) -> Any:
        """Path to the currently displayed log file."""
        value = self._pb_obj.get("logFile", self._pb_obj.get("currentLogPath"))
        return self._wrap("logFile", value)

    @log_path.setter
    def log_path(self, value: str) -> None:
        """Set the currently displayed log file."""
        self._pb_obj["logFile"] = _unwrap_setting_value(value)
        self._apply()

    @classmethod
    def _from_pb(
        cls,
        pb_obj,
        client: Client,
        solution_id: str | None = None,
        viewport_id: str | None = None,
        viewport=None,
    ) -> LogsViewportSettings:
        """Build from a metadata Struct."""
        return cls(pb_obj, client, solution_id, viewport_id, viewport)


# ---------------------------------------------------------------------------
# Viewport entity
# ---------------------------------------------------------------------------


class Viewport[TSettings: ViewportSettings](BaseEntity[models.Viewport]):
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

        return ViewportMetadata(pb_obj, self._client, self.solution_id, settings, setting_options)

    @property
    def settings(self) -> TSettings:
        """Read/write viewport settings."""
        view = self._resolve_view()
        pb_obj = self._pb.settings

        if view is None:
            return self._build_settings(ViewportSettings, pb_obj)

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            return self._build_settings(PlotViewportSettings, pb_obj)
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            return self._build_settings(ChartViewportSettings, pb_obj)
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            return self._build_settings(MeshViewportSettings, pb_obj)
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            return self._build_settings(ConvergenceTrackersViewportSettings, pb_obj)
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            return self._build_settings(ContactTrackersViewportSettings, pb_obj)
        elif view.type == models.ViewType.VIEW_TYPE_LOGS:
            return self._build_settings(LogsViewportSettings, pb_obj)

        return self._build_settings(ViewportSettings, pb_obj)

    @property
    def display_options(self):
        """Removed. Use ``viewport.settings`` instead."""
        raise AttributeError(
            "Viewport.display_options has been removed. Use viewport.settings instead."
        )

    def _build_settings(self, settings_type, pb_obj) -> ViewportSettings:
        """Build typed settings and attach associated read-only data."""
        settings = settings_type._from_pb(pb_obj, self._client, self.solution_id, self.id, self)
        settings._setting_options = _settings_to_dict(self._pb.setting_options)
        return settings

    @contextmanager
    def update_settings(self) -> Generator[TSettings, None, None]:
        """Batch settings updates in a single server call."""
        opts = self.settings
        opts._batch_mode = True
        try:
            yield opts
        finally:
            opts._batch_mode = False
            opts._apply()

    @property
    def size(self) -> float:
        """Size of the viewport as a percentage of its parent."""
        return self._pb.size

    @overload
    def set_view(self, view: PlotView, wait: bool = ...) -> Viewport[PlotViewportSettings]: ...
    @overload
    def set_view(self, view: ChartView, wait: bool = ...) -> Viewport[ChartViewportSettings]: ...
    @overload
    def set_view(self, view: MeshView, wait: bool = ...) -> Viewport[MeshViewportSettings]: ...
    @overload
    def set_view(self, view: View, wait: bool = ...) -> Viewport[ViewportSettings]: ...
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
