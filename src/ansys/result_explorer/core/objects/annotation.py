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

"""Annotations and hot spots of 3D viewports.

Annotation definitions are stored as plain objects in the ``annotations``
viewport setting, and the web UI publishes the annotations shown in the
scene in the ``resolvedAnnotations`` viewport metadata.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

HOT_SPOT_GROUP = "hotspots"
_GRAPHICS_SOURCE = "graphics"

type Vector3 = tuple[float, float, float]


class AnnotationTargetKind(StrEnum):
    """Kind of mesh entity an annotation is anchored to."""

    node = "node"
    element = "element"


class AnnotationPlacement(StrEnum):
    """Placement of the annotation card."""

    follow_scene = "followScene"
    screen_pinned = "screenPinned"


class AnnotationStatus(StrEnum):
    """Resolution status of an annotation in the scene."""

    resolved = "resolved"
    pending = "pending"
    inactive_set = "inactiveSet"
    inactive_result = "inactiveResult"
    unavailable_body = "unavailableBody"
    unavailable_target = "unavailableTarget"
    unavailable_results = "unavailableResults"


@dataclass(frozen=True)
class AnnotationTarget:
    """Mesh entity an annotation is anchored to."""

    kind: AnnotationTargetKind
    id: int
    body_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnnotationAnchor:
    """Location an annotation points to.

    A position, a mesh entity, or both. The displacement places the
    position in the deformed scene.
    """

    position: Vector3 | None = None
    target: AnnotationTarget | None = None
    displacement: Vector3 | None = None

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AnnotationAnchor:
        target = data.get("target")
        return cls(
            position=_vector3(data.get("position")),
            target=AnnotationTarget(
                kind=AnnotationTargetKind(target["kind"]),
                id=int(target["id"]),
                body_ids=tuple(str(b) for b in target.get("bodyIds", [])),
            )
            if target is not None
            else None,
            displacement=_vector3(data.get("displacement")),
        )

    def _to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.position is not None:
            data["position"] = list(self.position)
        if self.target is not None:
            data["target"] = {
                "kind": self.target.kind.value,
                "bodyIds": list(self.target.body_ids),
                "id": self.target.id,
            }
        if self.displacement is not None:
            data["displacement"] = list(self.displacement)
        return data


@dataclass(frozen=True)
class AnnotationResultReference:
    """Result an annotation shows; a given value wins over a lookup."""

    name: str | None = None
    component: str | None = None
    value: float | None = None

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AnnotationResultReference:
        return cls(name=data.get("name"), component=data.get("component"), value=data.get("value"))

    def _to_dict(self) -> dict[str, Any]:
        data = {"name": self.name, "component": self.component, "value": self.value}
        return {k: v for k, v in data.items() if v is not None}


@dataclass(frozen=True)
class AnnotationResult:
    """Result value resolved for an annotation in the scene."""

    name: str
    component: str
    value: float
    unit: str


_PROPERTY_VISIBILITY_KEYS = {
    "anchor_id": "anchorId",
    "anchor_body_label": "anchorBodyLabel",
    "mesh_location": "meshLocation",
    "deformed_location": "deformedLocation",
    "result_name": "resultName",
    "result_component": "resultComponent",
    "result_value": "resultValue",
    "note": "note",
}

# Defaults of the web UI for new annotations, without and with a result
_DEFAULT_MESH_PROPERTY_VISIBILITY = {"anchorId", "anchorBodyLabel", "meshLocation", "note"}
_DEFAULT_PLOT_PROPERTY_VISIBILITY = {"resultValue", "note"}


def _default_property_visibility(with_result: bool) -> dict[str, bool]:
    shown = _DEFAULT_PLOT_PROPERTY_VISIBILITY if with_result else _DEFAULT_MESH_PROPERTY_VISIBILITY
    return {key: key in shown for key in _PROPERTY_VISIBILITY_KEYS.values()}


def _read_only_error(name: str) -> AttributeError:
    return AttributeError(
        f"'{name}' is read-only. Add the annotation to 'viewport.settings.annotations' "
        "to edit its presentation."
    )


class AnnotationPropertyVisibility:
    """Visibility of each property on the annotation card."""

    _data: dict[str, Any]
    _on_change: Callable[[], None] | None

    def __init__(self, data: dict[str, Any], on_change: Callable[[], None] | None) -> None:
        """Wrap the ``propertyVisibility`` object of a definition."""
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_on_change", on_change)

    def __getattr__(self, name: str) -> bool:
        """Return the visibility of a card property."""
        if name not in _PROPERTY_VISIBILITY_KEYS:
            raise AttributeError(name)
        return bool(self._data.get(_PROPERTY_VISIBILITY_KEYS[name], False))

    def __setattr__(self, name: str, value: bool) -> None:
        """Set the visibility of a card property and apply it."""
        if name not in _PROPERTY_VISIBILITY_KEYS:
            raise AttributeError(name)
        if self._on_change is None:
            raise _read_only_error(f"property_visibility.{name}")
        self._data[_PROPERTY_VISIBILITY_KEYS[name]] = bool(value)
        self._on_change()

    def to_dict(self) -> dict[str, bool]:
        """Return the visibility of each card property."""
        return {name: getattr(self, name) for name in _PROPERTY_VISIBILITY_KEYS}

    def __repr__(self) -> str:
        """Return the visibility of each card property."""
        flags = ", ".join(f"{k}={v}" for k, v in self.to_dict().items())
        return f"AnnotationPropertyVisibility({flags})"


class Annotation:
    """Proxy for an annotation definition.

    The anchor, sets and result reference are read-only. The note,
    visibility, placement, card location and property visibility are
    editable when the annotation belongs to the viewport settings; each
    edit is applied to the viewport.
    """

    def __init__(self, data: dict[str, Any], on_change: Callable[[], None] | None = None) -> None:
        """Wrap a definition, editable when ``on_change`` is given."""
        self._data = data
        self._on_change = on_change

    def _set(self, key: str, value: object) -> None:
        if self._on_change is None:
            raise _read_only_error(key)
        if value is None:
            self._data.pop(key, None)
        else:
            self._data[key] = value
        self._on_change()

    @property
    def id(self) -> str:
        """Unique identifier, shared by a hot spot and its edited copy."""
        return self._data["id"]

    @property
    def group(self) -> str | None:
        """Group, ``"hotspots"`` for hot spots."""
        return self._data.get("group")

    @property
    def source(self) -> str | None:
        """Source, ``"graphics"`` for annotations delivered with the data."""
        return self._data.get("source")

    @property
    def is_hot_spot(self) -> bool:
        """Whether the annotation is a hot spot."""
        return self.group == HOT_SPOT_GROUP

    @property
    def set_ids(self) -> tuple[int, ...] | None:
        """Result sets the annotation is shown on, or None for all sets."""
        set_ids = self._data.get("setIds")
        return None if set_ids is None else tuple(int(s) for s in set_ids)

    @property
    def anchor(self) -> AnnotationAnchor:
        """Location the annotation points to."""
        return AnnotationAnchor._from_dict(self._data.get("anchor", {}))

    @property
    def result_reference(self) -> AnnotationResultReference | None:
        """Result the annotation shows, if any."""
        ref = self._data.get("resultReference")
        return None if ref is None else AnnotationResultReference._from_dict(ref)

    @property
    def note(self) -> str:
        """Free text shown on the card."""
        return self._data.get("note", "")

    @note.setter
    def note(self, value: str) -> None:
        self._set("note", value)

    @property
    def visibility(self) -> bool:
        """Whether the annotation is shown."""
        return bool(self._data.get("visibility", True))

    @visibility.setter
    def visibility(self, value: bool) -> None:
        self._set("visibility", bool(value))

    @property
    def placement(self) -> AnnotationPlacement:
        """Placement of the card."""
        return AnnotationPlacement(self._data.get("placement", "followScene"))

    @placement.setter
    def placement(self, value: AnnotationPlacement | str) -> None:
        self._set("placement", AnnotationPlacement(value).value)

    @property
    def card_screen_location(self) -> tuple[float, float] | None:
        """Location of a pinned card as fractions of the viewport.

        ``(0, 0)`` places the card at the top left and ``(1, 1)`` at the
        bottom right of the viewport.
        """
        location = self._data.get("cardScreenLocation")
        return None if location is None else (float(location[0]), float(location[1]))

    @card_screen_location.setter
    def card_screen_location(self, value: tuple[float, float] | None) -> None:
        if value is not None and not all(0.0 <= v <= 1.0 for v in value):
            raise ValueError("Card screen location fractions must be between 0 and 1.")
        self._set("cardScreenLocation", None if value is None else [value[0], value[1]])

    @property
    def property_visibility(self) -> AnnotationPropertyVisibility:
        """Visibility of each property on the card."""
        return AnnotationPropertyVisibility(
            self._data.setdefault("propertyVisibility", {}), self._on_change
        )

    def __repr__(self) -> str:
        """Return a short description of the annotation."""
        kind = "HotSpot" if self.is_hot_spot else "Annotation"
        return f"{type(self).__name__}<{kind}>(id={self.id!r}, note={self.note!r})"


class ResolvedAnnotation(Annotation):
    """Read-only annotation shown in the scene, with its resolved data."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Wrap a ``resolvedAnnotations`` metadata entry."""
        super().__init__(data.get("definition", {}))
        self._resolved = data

    @property
    def status(self) -> AnnotationStatus:
        """Resolution status in the scene."""
        return AnnotationStatus(self._resolved.get("status", "pending"))

    @property
    def body_hidden(self) -> bool:
        """Whether all the bodies of the anchor are hidden."""
        return bool(self._resolved.get("bodyHidden", False))

    @property
    def mesh_location(self) -> Vector3 | None:
        """Undeformed location of the anchor."""
        return _vector3(self._resolved.get("meshLocation"))

    @property
    def deformed_location(self) -> Vector3 | None:
        """Deformed location of the anchor."""
        return _vector3(self._resolved.get("deformedLocation"))

    @property
    def scene_location(self) -> Vector3 | None:
        """Location of the anchor in the displayed scene."""
        return _vector3(self._resolved.get("sceneLocation"))

    @property
    def result(self) -> AnnotationResult | None:
        """Resolved result value, if any."""
        result = self._resolved.get("result")
        if result is None:
            return None
        return AnnotationResult(
            name=result.get("name", ""),
            component=result.get("component", ""),
            value=float(result["value"]),
            unit=result.get("unit", ""),
        )

    def _definition(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)


class ViewportAnnotations:
    """Annotations stored in the settings of a 3D viewport.

    Items are live: editing one applies the settings to the viewport.
    """

    def __init__(self, items: list[dict[str, Any]], on_change: Callable[[], None]) -> None:
        """Wrap the ``annotations`` setting list."""
        self._items = items
        self._on_change = on_change

    def _wrap(self, data: dict[str, Any]) -> Annotation:
        return Annotation(data, self._on_change)

    def __len__(self) -> int:
        """Return the number of annotations."""
        return len(self._items)

    def __iter__(self) -> Iterator[Annotation]:
        """Iterate over the annotations."""
        return (self._wrap(item) for item in self._items)

    def __getitem__(self, key: int | str) -> Annotation:
        """Return an annotation by index or by ID."""
        if isinstance(key, int):
            return self._wrap(self._items[key])
        return self._wrap(self._items[self._index(key)])

    def __contains__(self, item: object) -> bool:
        """Return whether an annotation or ID is stored."""
        key = item.id if isinstance(item, Annotation) else item
        return any(data.get("id") == key for data in self._items)

    def _index(self, annotation_id: str) -> int:
        for index, data in enumerate(self._items):
            if data.get("id") == annotation_id:
                return index
        raise KeyError(annotation_id)

    def add(
        self,
        anchor: AnnotationAnchor,
        note: str = "",
        result_reference: AnnotationResultReference | None = None,
        set_ids: list[int] | None = None,
        placement: AnnotationPlacement = AnnotationPlacement.follow_scene,
        visibility: bool = True,
        id: str | None = None,
    ) -> Annotation:
        """Add a user annotation.

        Parameters
        ----------
        anchor : AnnotationAnchor
            Location the annotation points to.
        note : str, default: ""
            Free text shown on the card.
        result_reference : AnnotationResultReference, optional
            Result to show. Without it, the card shows mesh properties.
        set_ids : list[int], optional
            Result sets to show the annotation on. All sets by default.
        placement : AnnotationPlacement, default: follow_scene
            Placement of the card.
        visibility : bool, default: True
            Whether the annotation is shown.
        id : str, optional
            Unique identifier. A random one by default.

        Returns
        -------
        Annotation
            Editable annotation.

        """
        data: dict[str, Any] = {
            "id": id or str(uuid.uuid4()),
            "anchor": anchor._to_dict(),
            "note": note,
            "placement": AnnotationPlacement(placement).value,
            "visibility": visibility,
            "propertyVisibility": _default_property_visibility(result_reference is not None),
        }
        if result_reference is not None:
            data["resultReference"] = result_reference._to_dict()
        if set_ids is not None:
            data["setIds"] = list(set_ids)
        return self._append(data)

    def _append(self, data: dict[str, Any]) -> Annotation:
        if data["id"] in self:
            raise ValueError(f"Annotation {data['id']!r} already exists.")
        self._items.append(data)
        self._on_change()
        return self._wrap(data)

    def remove(self, annotation: Annotation | str) -> None:
        """Remove an annotation, restoring a hot spot to its original presentation."""
        key = annotation.id if isinstance(annotation, Annotation) else annotation
        del self._items[self._index(key)]
        self._on_change()

    def clear(self) -> None:
        """Remove all the annotations."""
        self._items.clear()
        self._on_change()

    def __repr__(self) -> str:
        """Return the stored annotations."""
        return f"{type(self).__name__}({list(self)!r})"


class PlotViewportAnnotations(ViewportAnnotations):
    """Annotations stored in the settings of a plot viewport.

    Besides user annotations, holds the edited copies of hot spots.
    """

    def add_hot_spot(self, hot_spot: ResolvedAnnotation) -> Annotation:
        """Store an editable copy of a hot spot.

        The copy keeps the ID of the hot spot, so its presentation
        replaces the presentation of the hot spot. The anchor and result
        always come from the hot spot data. An existing copy is returned
        unchanged.

        Parameters
        ----------
        hot_spot : ResolvedAnnotation
            Hot spot from ``viewport.metadata.hot_spots``.

        Returns
        -------
        Annotation
            Editable copy of the hot spot.

        """
        if not hot_spot.is_hot_spot:
            raise ValueError(f"Annotation {hot_spot.id!r} is not a hot spot.")
        if hot_spot.id in self:
            return self[hot_spot.id]
        data = hot_spot._definition()
        data["source"] = _GRAPHICS_SOURCE
        return self._append(data)


def _vector3(value: list[float] | None) -> Vector3 | None:
    if value is None or len(value) != 3:
        return None
    return (float(value[0]), float(value[1]), float(value[2]))
