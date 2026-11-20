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


@dataclass(frozen=True)
class AnnotationTarget:
    """Mesh entity an annotation is anchored to."""

    kind: AnnotationTargetKind
    id: int
    body_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnnotationAnchor:
    """Location an annotation points to: a position, a mesh entity, or both."""

    position: Vector3 | None = None
    """Anchor position, for an annotation without a target, or whose
    target is in the interior of the mesh rather than on the skin."""
    target: AnnotationTarget | None = None
    """Mesh entity the annotation is anchored to."""
    displacement: Vector3 | None = None
    """Displacement at the anchor position, used when the target is in the
    interior of the mesh."""

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
    """Result an annotation shows.

    An unset ``name`` or ``component`` follows the result or component
    displayed in the viewport (dynamic). A set one locks the annotation
    to it: the annotation is shown only while the viewport displays that
    result and component. ``""`` is the magnitude, or the value of a
    single-component result. A given ``value`` wins over a lookup.
    """

    name: str | None = None
    """Result name, such as ``"displacement"``, or None to follow the viewport."""
    component: str | None = None
    """Component, such as ``"X"`` or ``""`` for the magnitude, or None to
    follow the viewport."""
    value: float | None = None
    """Given value, shown instead of the value looked up at the anchor."""

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
        f"'{name}' is read-only. Edit annotations and hot spots through "
        "'viewport.annotations' and 'viewport.hot_spots'."
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
    """Read-only view of an annotation definition.

    Returned by ``viewport.settings.annotations``, which lists the stored
    definitions, including the edited copies of hot spots.
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
    def card_offset(self) -> tuple[float, float] | None:
        """Pixel gaps ``(left_gap, down_gap)`` of a scene-following card.

        The card's left edge is the projected anchor's X coordinate minus
        the card width and ``left_gap``. Its top edge is the projected
        anchor's Y coordinate plus ``down_gap``. ``None`` uses the web UI
        default. Setting this does not pin the card.
        """
        offset = self._data.get("cardOffset")
        return None if offset is None else (float(offset[0]), float(offset[1]))

    @card_offset.setter
    def card_offset(self, value: tuple[float, float] | None) -> None:
        self._set("cardOffset", None if value is None else [value[0], value[1]])

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


class _SceneResolution:
    """Resolution of an annotation in the scene, published by the web UI."""

    def _resolution(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def status(self) -> str | None:
        """Resolution status in the scene, or None until it is resolved.

        ``"resolved"`` when the annotation is shown. Other values tell why
        it isn't: ``"pending"``, ``"inactiveSet"``, ``"inactiveResult"``,
        ``"unavailableBody"``, ``"unavailableTarget"`` or
        ``"unavailableResults"``.
        """
        return self._resolution().get("status")

    @property
    def body_hidden(self) -> bool:
        """Whether all the bodies of the anchor are hidden."""
        return bool(self._resolution().get("bodyHidden", False))

    @property
    def mesh_location(self) -> Vector3 | None:
        """Undeformed location of the anchor."""
        return _vector3(self._resolution().get("meshLocation"))

    @property
    def deformed_location(self) -> Vector3 | None:
        """Deformed location of the anchor."""
        return _vector3(self._resolution().get("deformedLocation"))

    @property
    def scene_location(self) -> Vector3 | None:
        """Location of the anchor in the displayed scene."""
        return _vector3(self._resolution().get("sceneLocation"))

    @property
    def result(self) -> AnnotationResult | None:
        """Resolved result value, if any."""
        result = self._resolution().get("result")
        if result is None:
            return None
        return AnnotationResult(
            name=result.get("name", ""),
            component=result.get("component", ""),
            value=float(result["value"]),
            unit=result.get("unit", ""),
        )


class ResolvedAnnotation(Annotation, _SceneResolution):
    """Read-only annotation shown in the scene, with its resolved data."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Wrap a ``resolvedAnnotations`` metadata entry."""
        super().__init__(data.get("definition", {}))
        self._resolved = data

    def _resolution(self) -> dict[str, Any]:
        return self._resolved

    def _definition(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)


# Returns the annotation definitions of the viewport settings and the
# function applying them. With ``True``, for an edit: the definitions are
# read from the current viewport state first, so edits made since this
# object was read aren't overwritten. Inside ``viewport.update_settings()``,
# these are the batched settings.
type AnnotationStore = Callable[[bool], tuple[list[dict[str, Any]], Callable[[], None]]]
type AnnotationResolver = Callable[[str], dict[str, Any] | None]


def _find(items: list[dict[str, Any]], annotation_id: str) -> dict[str, Any] | None:
    return next((data for data in items if data.get("id") == annotation_id), None)


class _LiveAnnotation(_SceneResolution):
    """Annotation of a viewport, looked up by ID on every access.

    Reading or editing always uses the current viewport settings, so
    proxies stay consistent with each other and with other setting edits.
    """

    def __init__(self, annotation_id: str, store: AnnotationStore) -> None:
        self._id = annotation_id
        self._store = store

    def _current(self) -> Annotation:
        raise NotImplementedError

    def _edit(self, edit: Callable[[Annotation], None]) -> None:
        raise NotImplementedError

    @property
    def id(self) -> str:
        """Unique identifier."""
        return self._id

    @property
    def set_ids(self) -> tuple[int, ...] | None:
        """Result sets the annotation is shown on, or None for all sets."""
        return self._current().set_ids

    @property
    def anchor(self) -> AnnotationAnchor:
        """Location the annotation points to."""
        return self._current().anchor

    @property
    def result_reference(self) -> AnnotationResultReference | None:
        """Result the annotation shows, if any."""
        return self._current().result_reference

    @property
    def note(self) -> str:
        """Free text shown on the card."""
        return self._current().note

    @note.setter
    def note(self, value: str) -> None:
        self._edit(lambda a: setattr(a, "note", value))

    @property
    def visibility(self) -> bool:
        """Whether the annotation is shown."""
        return self._current().visibility

    @visibility.setter
    def visibility(self, value: bool) -> None:
        self._edit(lambda a: setattr(a, "visibility", value))

    @property
    def placement(self) -> AnnotationPlacement:
        """Placement of the card."""
        return self._current().placement

    @placement.setter
    def placement(self, value: AnnotationPlacement | str) -> None:
        self._edit(lambda a: setattr(a, "placement", value))

    @property
    def card_screen_location(self) -> tuple[float, float] | None:
        """Location of a pinned card as fractions of the viewport.

        ``(0, 0)`` places the card at the top left and ``(1, 1)`` at the
        bottom right of the viewport.
        """
        return self._current().card_screen_location

    @card_screen_location.setter
    def card_screen_location(self, value: tuple[float, float] | None) -> None:
        self._edit(lambda a: setattr(a, "card_screen_location", value))

    @property
    def card_offset(self) -> tuple[float, float] | None:
        """Pixel gaps ``(left_gap, down_gap)`` of a scene-following card.

        See ``Annotation.card_offset`` for the positioning formula.
        None uses the web UI default of ``(24, 24)``. Setting this does
        not pin the card.
        """
        return self._current().card_offset

    @card_offset.setter
    def card_offset(self, value: tuple[float, float] | None) -> None:
        self._edit(lambda a: setattr(a, "card_offset", value))

    @property
    def property_visibility(self) -> AnnotationPropertyVisibility:
        """Visibility of each property on the card."""
        data = dict(self._current()._data.get("propertyVisibility", {}))

        def write() -> None:
            self._edit(lambda a: a._set("propertyVisibility", dict(data)))

        return AnnotationPropertyVisibility(data, write)

    def __repr__(self) -> str:
        """Return a short description of the annotation."""
        return f"{type(self).__name__}(id={self.id!r}, note={self.note!r})"


class ViewportAnnotation(_LiveAnnotation):
    """User annotation of a 3D viewport.

    The anchor is set when the annotation is added. The note, visibility,
    placement, card location, card offset and property visibility are
    editable, as are the sets and result reference that make a plot
    annotation dynamic or locked; each edit applies to the viewport.
    The resolution in the scene
    (status, locations, result) is published by the web UI once the scene
    is rendered, and is unset until then.

    A plot annotation is dynamic when ``set_ids`` and the ``name`` and
    ``component`` of its ``result_reference`` are None: it shows the value
    of the set, result and component displayed in the viewport. Setting
    them locks it: it is shown only while the viewport displays them, and
    its status is ``"inactiveSet"`` or ``"inactiveResult"`` otherwise.
    Each of the three can be locked separately.
    """

    def __init__(
        self, annotation_id: str, store: AnnotationStore, resolve: AnnotationResolver
    ) -> None:
        """Bind an annotation ID to the viewport settings and metadata."""
        super().__init__(annotation_id, store)
        self._resolve = resolve

    def _resolution(self) -> dict[str, Any]:
        return self._resolve(self._id) or {}

    def _lookup(self, edit: bool) -> tuple[dict[str, Any], Callable[[], None]]:
        items, apply = self._store(edit)
        data = _find(items, self._id)
        if data is None:
            raise LookupError(f"Annotation {self._id!r} was removed from the viewport.")
        return data, apply

    def _current(self) -> Annotation:
        return Annotation(self._lookup(False)[0])

    def _edit(self, edit: Callable[[Annotation], None]) -> None:
        edit(Annotation(*self._lookup(True)))

    @property
    def set_ids(self) -> tuple[int, ...] | None:
        """Result sets the annotation is locked to, or None to follow the viewport."""
        return self._current().set_ids

    @set_ids.setter
    def set_ids(self, value: list[int] | tuple[int, ...] | None) -> None:
        set_ids = _set_ids_value(value)
        self._edit(lambda a: a._set("setIds", set_ids))

    @property
    def result_reference(self) -> AnnotationResultReference | None:
        """Result the annotation shows, or None for mesh properties only."""
        return self._current().result_reference

    @result_reference.setter
    def result_reference(self, value: AnnotationResultReference | None) -> None:
        self._edit(lambda a: a._set("resultReference", None if value is None else value._to_dict()))


class HotSpot(_LiveAnnotation):
    """Hot spot of a plot viewport.

    The anchor, sets, result reference and resolved result come from the
    data and are read-only. The note, visibility, placement, card location,
    card offset and property visibility are editable: the first edit
    stores an edited copy in the viewport settings, and ``reset()``
    removes it.
    """

    def __init__(self, resolved: ResolvedAnnotation, store: AnnotationStore) -> None:
        """Bind a resolved hot spot to the viewport settings."""
        super().__init__(resolved.id, store)
        self._resolved = resolved

    def _resolution(self) -> dict[str, Any]:
        return self._resolved._resolution()

    def _current(self) -> Annotation:
        items, _ = self._store(False)
        data = _find(items, self._id)
        return self._resolved if data is None else Annotation(data)

    def _edit(self, edit: Callable[[Annotation], None]) -> None:
        items, apply = self._store(True)
        data = _find(items, self._id)
        if data is not None:
            edit(Annotation(data, apply))
            return
        data = self._resolved._definition()
        data["source"] = _GRAPHICS_SOURCE
        edit(Annotation(data, lambda: None))
        items.append(data)
        apply()

    @property
    def is_edited(self) -> bool:
        """Whether the presentation of the hot spot was edited."""
        return _find(self._store(False)[0], self._id) is not None

    def reset(self) -> None:
        """Remove the edits, restoring the original presentation."""
        items, apply = self._store(True)
        data = _find(items, self._id)
        if data is not None:
            items.remove(data)
            apply()


class ViewportAnnotations:
    """User annotations of a 3D viewport.

    Items are looked up by ID in the current viewport settings, and edits
    apply to the viewport. The edited copies of hot spots are listed in
    ``viewport.hot_spots`` instead.
    """

    def __init__(self, store: AnnotationStore, resolve: AnnotationResolver) -> None:
        """Bind to the viewport settings and metadata."""
        self._store = store
        self._resolve = resolve

    def _ids(self) -> list[str]:
        items, _ = self._store(False)
        return [d["id"] for d in items if d.get("source") != _GRAPHICS_SOURCE and "id" in d]

    def _wrap(self, annotation_id: str) -> ViewportAnnotation:
        return ViewportAnnotation(annotation_id, self._store, self._resolve)

    def __len__(self) -> int:
        """Return the number of annotations."""
        return len(self._ids())

    def __iter__(self) -> Iterator[ViewportAnnotation]:
        """Iterate over the annotations."""
        return (self._wrap(annotation_id) for annotation_id in self._ids())

    def __getitem__(self, key: int | str) -> ViewportAnnotation:
        """Return an annotation by index or by ID."""
        ids = self._ids()
        if isinstance(key, int):
            return self._wrap(ids[key])
        if key not in ids:
            raise KeyError(key)
        return self._wrap(key)

    def __contains__(self, item: object) -> bool:
        """Return whether an annotation or ID is stored."""
        key = item.id if isinstance(item, ViewportAnnotation) else item
        return key in self._ids()

    def add(
        self,
        anchor: AnnotationAnchor,
        note: str = "",
        result_reference: AnnotationResultReference | None = None,
        set_ids: list[int] | None = None,
        placement: AnnotationPlacement = AnnotationPlacement.follow_scene,
        visibility: bool = True,
        id: str | None = None,
    ) -> ViewportAnnotation:
        """Add a user annotation.

        Parameters
        ----------
        anchor : AnnotationAnchor
            Location the annotation points to.
        note : str, default: ""
            Free text shown on the card.
        result_reference : AnnotationResultReference, optional
            Result to show. Without it, the card shows mesh properties.
            ``AnnotationResultReference()`` follows the result and
            component displayed in the viewport; a ``name`` or
            ``component`` locks the annotation to them.
        set_ids : list[int], optional
            Result sets to lock the annotation to. By default, it follows
            the set displayed in the viewport.
        placement : AnnotationPlacement, default: follow_scene
            Placement of the card.
        visibility : bool, default: True
            Whether the annotation is shown.
        id : str, optional
            Unique identifier. A random one by default.

        Returns
        -------
        ViewportAnnotation
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
            data["setIds"] = _set_ids_value(set_ids)
        items, apply = self._store(True)
        if _find(items, data["id"]) is not None:
            raise ValueError(f"Annotation {data['id']!r} already exists.")
        items.append(data)
        apply()
        return self._wrap(data["id"])

    def remove(self, annotation: ViewportAnnotation | str) -> None:
        """Remove an annotation."""
        key = annotation.id if isinstance(annotation, ViewportAnnotation) else annotation
        items, apply = self._store(True)
        data = _find(items, key)
        if data is None or data.get("source") == _GRAPHICS_SOURCE:
            raise KeyError(key)
        items.remove(data)
        apply()

    def clear(self) -> None:
        """Remove all the user annotations; hot spot edits are kept."""
        items, apply = self._store(True)
        items[:] = [d for d in items if d.get("source") == _GRAPHICS_SOURCE]
        apply()

    def __repr__(self) -> str:
        """Return the stored annotations."""
        return f"ViewportAnnotations({list(self)!r})"


def _set_ids_value(value: list[int] | tuple[int, ...] | None) -> list[int] | None:
    if value is None:
        return None
    if not value:
        raise ValueError("set_ids must list at least one set, or be None to follow the viewport.")
    return [int(set_id) for set_id in value]


def _vector3(value: list[float] | None) -> Vector3 | None:
    if value is None or len(value) != 3:
        return None
    return (float(value[0]), float(value[1]), float(value[2]))
