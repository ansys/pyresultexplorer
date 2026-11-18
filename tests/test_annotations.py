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

import time
from collections.abc import Callable
from typing import cast

import pytest
from google.protobuf import struct_pb2

from ansys.result_explorer.core import (
    AnnotationAnchor,
    AnnotationPlacement,
    AnnotationResultReference,
    AnnotationTarget,
    AnnotationTargetKind,
    Client,
    Field,
    HotSpot,
    HotSpotDefinition,
    HotSpotKind,
    PlotDefinition,
    PlotViewportMetadata,
    PlotViewportSettings,
    ResolvedAnnotation,
    ResultFieldName,
    ResultType,
    ThreeDViewportMetadata,
    ViewportAnnotations,
    models,
)
from ansys.result_explorer.core.objects.viewport import (
    Viewport,
    _dict_to_settings,
    _settings_to_dict,
)

NO_CLIENT = cast(Client, None)

HOT_SPOT = {
    "definition": {
        "id": "max:1",
        "group": "hotspots",
        "source": "graphics",
        "setIds": [1.0],
        "anchor": {
            "position": [1.0, 2.0, 3.0],
            "target": {"kind": "node", "bodyIds": ["4"], "id": 12.0},
            "displacement": [0.0, 0.0, 0.5],
        },
        "note": "",
        "resultReference": {"name": "stress", "component": "", "value": 250.0},
        "placement": "followScene",
        "visibility": True,
        "propertyVisibility": {"resultValue": True, "note": True},
    },
    "status": "resolved",
    "bodyHidden": False,
    "meshLocation": [1.0, 2.0, 3.0],
    "deformedLocation": [1.0, 2.0, 3.5],
    "sceneLocation": [1.0, 2.0, 3.5],
    "result": {"name": "stress", "component": "", "value": 250.0, "unit": "Pa"},
}


def _offline_settings(settings: dict) -> PlotViewportSettings:
    opts = PlotViewportSettings._from_pb(
        _dict_to_settings(settings), client=NO_CLIENT, viewport_id="vp"
    )
    opts._batch_mode = True
    return opts


def _round_trip(opts: PlotViewportSettings) -> dict:
    return _settings_to_dict(opts._to_pb())


def test_plot_definition_hot_spot_round_trip():
    definition = PlotDefinition(
        result_type=ResultType.stress,
        location="Nodal",
        fields=[Field(name=ResultFieldName.equivalent_von_mises_stress)],
        hot_spot_definition=HotSpotDefinition(
            kind=HotSpotKind.maximum, num_hotspots=5, threshold_low=1.5
        ),
    )

    restored = PlotDefinition.from_proto(definition.to_proto(models.PlotDefinition))
    assert restored.hot_spot_definition == definition.hot_spot_definition
    restored = PlotDefinition.from_proto(definition.to_proto(models.PlotDefinitionCreate))
    assert restored.hot_spot_definition == definition.hot_spot_definition

    definition.hot_spot_definition = None
    restored = PlotDefinition.from_proto(definition.to_proto(models.PlotDefinition))
    assert restored.hot_spot_definition is None


def test_resolved_hot_spot_is_read_only():
    struct = struct_pb2.Struct()
    struct.update({"resolvedAnnotations": [HOT_SPOT]})
    metadata = PlotViewportMetadata(struct, NO_CLIENT)

    (hot_spot,) = metadata.hot_spots
    assert hot_spot.id == "max:1"
    assert hot_spot.set_ids == (1,)
    assert hot_spot.status == "resolved"
    assert hot_spot.anchor.target == AnnotationTarget(AnnotationTargetKind.node, 12, ("4",))
    assert hot_spot.deformed_location == (1.0, 2.0, 3.5)
    assert hot_spot.result is not None
    assert hot_spot.result.unit == "Pa"
    assert hot_spot.result_reference == AnnotationResultReference("stress", "", 250.0)

    with pytest.raises(AttributeError, match="read-only"):
        hot_spot.note = "edited"
    with pytest.raises(AttributeError, match="read-only"):
        hot_spot.property_visibility.result_name = True

    mesh_metadata = ThreeDViewportMetadata(struct, NO_CLIENT)
    assert len(mesh_metadata.resolved_annotations) == 1
    assert not hasattr(mesh_metadata, "hot_spots")


class _OfflineStore:
    """Annotation store over offline plot settings, counting the applies."""

    def __init__(self, settings: dict) -> None:
        self.opts = _offline_settings(settings)
        self.applies = 0

    def __call__(self, edit: bool = False) -> tuple[list[dict], Callable[[], None]]:
        def apply() -> None:
            self.applies += 1

        return self.opts._annotation_items(), apply

    def saved(self) -> list[dict]:
        return _round_trip(self.opts)["annotations"]


def test_hot_spot_edits_store_a_copy():
    store = _OfflineStore({"annotations": None})
    hot_spot = HotSpot(ResolvedAnnotation(HOT_SPOT), store)
    assert not hot_spot.is_edited
    assert hot_spot.result is not None
    assert hot_spot.result.value == 250.0

    hot_spot.note = "Max stress"
    hot_spot.property_visibility.result_name = True

    assert store.applies == 2
    assert hot_spot.is_edited
    (stored,) = store.saved()
    assert stored["id"] == "max:1"
    assert stored["source"] == "graphics"
    assert stored["note"] == "Max stress"
    assert stored["propertyVisibility"] == {"resultValue": True, "note": True, "resultName": True}
    assert stored["resultReference"]["value"] == 250.0
    assert HotSpot(ResolvedAnnotation(HOT_SPOT), store).note == "Max stress"
    assert [a.id for a in store.opts.annotations] == ["max:1"]

    with pytest.raises(AttributeError):
        hot_spot.anchor = AnnotationAnchor()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        hot_spot.set_ids = [2]  # type: ignore[misc]
    with pytest.raises(AttributeError):
        hot_spot.result_reference = AnnotationResultReference()  # type: ignore[misc]

    hot_spot.reset()
    assert not hot_spot.is_edited
    assert hot_spot.note == ""
    assert store.saved() == []


def test_viewport_annotations():
    store = _OfflineStore({})
    resolution = {"status": "resolved", "meshLocation": [0.0, 0.0, 0.1]}
    annotations = ViewportAnnotations(store, lambda i: resolution if i == "a1" else None)
    HotSpot(ResolvedAnnotation(HOT_SPOT), store).visibility = False
    anchor = AnnotationAnchor(position=(0.0, 0.0, 0.1))

    annotation = annotations.add(anchor, note="Origin", id="a1")
    assert annotation.property_visibility.mesh_location is True
    assert annotation.property_visibility.result_value is False
    assert annotation.status == "resolved"
    assert annotation.mesh_location == (0.0, 0.0, 0.1)
    with_result = annotations.add(anchor, result_reference=AnnotationResultReference("s"))
    assert with_result.property_visibility.result_value is True
    assert with_result.status is None
    annotations.remove(with_result)

    annotations["a1"].placement = AnnotationPlacement.screen_pinned
    annotation.card_screen_location = (0.5, 1.0)
    assert annotation.placement == AnnotationPlacement.screen_pinned
    assert annotations[0].card_screen_location == (0.5, 1.0)

    with pytest.raises(ValueError, match="between 0 and 1"):
        annotation.card_screen_location = (10.0, 20.0)
    with pytest.raises(ValueError, match="already exists"):
        annotations.add(anchor, id="a1")
    with pytest.raises(KeyError):
        annotations.remove("max:1")

    assert len(annotations) == 1
    assert "max:1" not in annotations
    annotations.clear()
    assert len(annotations) == 0
    assert [a["id"] for a in store.saved()] == ["max:1"]
    with pytest.raises(LookupError, match="removed"):
        _ = annotation.note


def test_dynamic_and_locked_annotations():
    store = _OfflineStore({})
    annotations = ViewportAnnotations(store, lambda _: None)
    anchor = AnnotationAnchor(position=(0.0, 0.0, 0.1))

    dynamic = annotations.add(anchor, result_reference=AnnotationResultReference(), id="d")
    locked = annotations.add(
        anchor,
        result_reference=AnnotationResultReference("displacement", ""),
        set_ids=[3],
        id="l",
    )
    assert dynamic.set_ids is None
    assert dynamic.result_reference == AnnotationResultReference()
    assert locked.set_ids == (3,)

    dynamic.set_ids = [1, 2]
    dynamic.result_reference = AnnotationResultReference("displacement", "X")
    locked.set_ids = None
    locked.result_reference = AnnotationResultReference()

    stored = {a["id"]: a for a in store.saved()}
    assert stored["d"]["setIds"] == [1, 2]
    assert stored["d"]["resultReference"] == {"name": "displacement", "component": "X"}
    assert "setIds" not in stored["l"]
    assert stored["l"]["resultReference"] == {}

    with pytest.raises(ValueError, match="at least one set"):
        dynamic.set_ids = []
    with pytest.raises(ValueError, match="at least one set"):
        annotations.add(anchor, set_ids=[])


def test_hot_spot_display_options():
    opts = _offline_settings({"hotSpotsMaxNumber": 5, "hotSpotsThresholdRange": {"low": 1.0}})

    assert opts.hot_spots_max_number == 5
    assert opts.hot_spots_threshold_range == (1.0, None)
    assert opts.hot_spots_by_entity is None

    opts.hot_spots_max_number = None
    opts.hot_spots_by_entity = True
    opts.hot_spots_separation_distance = 0.01
    opts.hot_spots_threshold_range = (None, 2.0)

    raw = _round_trip(opts)
    assert raw["hotSpotsMaxNumber"] is None
    assert raw["hotSpotsByEntity"] is True
    assert raw["hotSpotsSeparationDistance"] == 0.01
    assert raw["hotSpotsThresholdRange"] == {"high": 2.0}


def _wait_for_metadata(
    rx,
    workspace_id: str,
    viewport_id: str,
    condition: Callable[[Viewport], bool],
    timeout: float = 60.0,
) -> Viewport:
    deadline = time.monotonic() + timeout
    while True:
        viewport = next(v for v in rx.get_workspace(workspace_id).viewports if v.id == viewport_id)
        if condition(viewport) or time.monotonic() > deadline:
            return viewport
        time.sleep(1)


def _hot_spots(viewport: Viewport) -> list[HotSpot]:
    return viewport.hot_spots


def _resolved_note_of(viewport: Viewport, annotation_id: str) -> str | None:
    metadata = viewport.metadata
    assert isinstance(metadata, PlotViewportMetadata)
    return next((h.note for h in metadata.hot_spots if h.id == annotation_id), None)


def test_hot_spots(rx, multiple_connections_solution):
    sol = multiple_connections_solution
    plot = sol.create_plot(
        PlotDefinition(
            result_type=ResultType.stress,
            location="Nodal",
            name="EQV hot spots",
            fields=[Field(name=ResultFieldName.equivalent_von_mises_stress)],
        )
    )
    definition = plot.definition
    definition.hot_spot_definition = HotSpotDefinition(kind=HotSpotKind.maximum, num_hotspots=5)
    plot = sol.update_plot(definition)
    assert plot.definition.hot_spot_definition == definition.hot_spot_definition

    workspace = rx.create_workspace("Hot spots")
    viewport = workspace.assign_view(view=plot, wait=True)
    viewport = _wait_for_metadata(rx, workspace.id, viewport.id, lambda v: bool(_hot_spots(v)))

    hot_spots = _hot_spots(viewport)
    assert 0 < len(hot_spots) <= 5
    values = [h.result.value for h in hot_spots if h.result is not None]
    assert values == sorted(values, reverse=True)

    hot_spot = hot_spots[0]
    with viewport.update_settings() as settings:
        settings.hot_spots_max_number = 2
        hot_spot.note = "Max stress"
        hot_spot.property_visibility.result_name = True

    assert hot_spot.note == "Max stress"
    assert viewport.settings.hot_spots_max_number == 2
    viewport = _wait_for_metadata(
        rx, workspace.id, viewport.id, lambda v: _resolved_note_of(v, hot_spot.id) == "Max stress"
    )
    edited = next(h for h in _hot_spots(viewport) if h.id == hot_spot.id)
    assert edited.is_edited
    assert edited.property_visibility.result_name is True
    assert edited.result_reference == hot_spot.result_reference

    edited.reset()
    assert not edited.is_edited
    assert viewport.settings.annotations == []


def test_annotations_and_hot_spots_by_view_type(rx, multiple_connections_solution):
    sol = multiple_connections_solution
    workspace = rx.create_workspace("Mesh annotations")
    viewport = workspace.assign_view(view=sol.mesh_view, wait=True)

    annotation = viewport.annotations.add(AnnotationAnchor(position=(0.0, 0.0, 0.0)), note="O")
    assert [a.note for a in viewport.annotations] == ["O"]
    viewport = _wait_for_metadata(
        rx, workspace.id, viewport.id, lambda v: v.annotations[annotation.id].status is not None
    )
    assert viewport.annotations[annotation.id].status == "resolved"

    # An item read from an older Viewport object joins the batch of a newer one
    with viewport.update_settings() as settings:
        settings.show_mesh_edges = True
        annotation.note = "Batched"
    viewport = next(v for v in rx.get_workspace(workspace.id).viewports if v.id == viewport.id)
    assert viewport.annotations[annotation.id].note == "Batched"
    assert viewport.settings.show_mesh_edges.value is True

    with pytest.raises(TypeError, match="plot viewports"):
        _ = viewport.hot_spots

    empty_viewport = workspace.create_viewport(
        viewport, models.ViewportDirection.VIEWPORT_DIRECTION_RIGHT
    )
    with pytest.raises(TypeError, match="plot and mesh"):
        _ = empty_viewport.annotations


def _hot_spot_values(viewport: Viewport) -> list[float]:
    return [h.result.value for h in _hot_spots(viewport) if h.result is not None]


def test_hot_spots_refresh_on_plot_update(rx, multiple_connections_solution):
    sol = multiple_connections_solution
    definition = PlotDefinition(
        name="Hot spots plot",
        result_type=ResultType.stress,
        location="Nodal",
        fields=[Field(name=ResultFieldName.equivalent_von_mises_stress)],
        hot_spot_definition=HotSpotDefinition(kind=HotSpotKind.minimum, num_hotspots=3),
    )
    plot = sol.create_plot(definition)
    workspace = rx.create_workspace("Hot spots refresh")
    viewport = workspace.assign_view(view=plot, wait=True)
    viewport = _wait_for_metadata(rx, workspace.id, viewport.id, lambda v: bool(_hot_spots(v)))
    lowest = max(_hot_spot_values(viewport))

    definition = plot.definition
    definition.hot_spot_definition = HotSpotDefinition(kind=HotSpotKind.maximum, num_hotspots=3)
    sol.update_plot(definition)

    viewport = _wait_for_metadata(
        rx,
        workspace.id,
        viewport.id,
        lambda v: min(_hot_spot_values(v), default=0.0) > lowest,
        timeout=20.0,
    )
    assert min(_hot_spot_values(viewport)) > lowest


def _available_results(viewport: Viewport) -> list[str]:
    metadata = viewport.metadata
    assert isinstance(metadata, PlotViewportMetadata)
    return metadata.available_results


def test_plot_update_refreshes_open_viewport(rx, multiple_connections_solution):
    sol = multiple_connections_solution
    plot = sol.create_plot(
        PlotDefinition(
            result_type=ResultType.stress,
            location="Nodal",
            fields=[Field(name=ResultFieldName.equivalent_von_mises_stress)],
        )
    )
    workspace = rx.create_workspace("Plot refresh")
    viewport = workspace.assign_view(view=plot, wait=True)
    viewport = _wait_for_metadata(
        rx, workspace.id, viewport.id, lambda v: bool(_available_results(v))
    )
    assert _available_results(viewport) == [ResultFieldName.equivalent_von_mises_stress]

    definition = plot.definition
    definition.fields = [Field(name=ResultFieldName.principal_stress_1)]
    plot = sol.update_plot(definition)
    assert plot.definition.fields == definition.fields

    viewport = _wait_for_metadata(
        rx,
        workspace.id,
        viewport.id,
        lambda v: _available_results(v) == [ResultFieldName.principal_stress_1],
        timeout=20.0,
    )
    assert _available_results(viewport) == [ResultFieldName.principal_stress_1]


def _status_and_value(viewport: Viewport, annotation_id: str) -> tuple[str | None, float | None]:
    annotation = viewport.annotations[annotation_id]
    return annotation.status, annotation.result.value if annotation.result else None


def test_dynamic_and_locked_plot_annotations(rx, cp_transient_solution):
    sol = cp_transient_solution
    first_set, last_set = sol.time_frequencies[0].set_id, sol.time_frequencies[-1].set_id
    workspace = rx.create_workspace("Locked annotations")
    view = sol.create_plot(
        PlotDefinition(
            result_type=ResultType.displacement,
            location="Nodal",
            name="Displacement, all sets",
            fields=[Field(name=ResultFieldName.displacement)],
            all_sets=True,
            last_set=False,
        )
    )
    viewport = workspace.assign_view(view=view, wait=True)
    # The web UI selects the initial set once the plot is loaded
    viewport = _wait_for_metadata(
        rx, workspace.id, viewport.id, lambda v: bool(_available_results(v)), timeout=30.0
    )
    viewport.settings.set_id = first_set
    anchor = AnnotationAnchor(
        target=AnnotationTarget(AnnotationTargetKind.node, 10, (sol.bodies[0].id,))
    )

    dynamic = viewport.annotations.add(anchor, result_reference=AnnotationResultReference())
    locked = viewport.annotations.add(
        anchor,
        result_reference=AnnotationResultReference(name="displacement", component=""),
        set_ids=[first_set],
    )

    def both(condition: Callable[[tuple, tuple], bool]) -> Viewport:
        return _wait_for_metadata(
            rx,
            workspace.id,
            viewport.id,
            lambda v: condition(_status_and_value(v, dynamic.id), _status_and_value(v, locked.id)),
            timeout=30.0,
        )

    viewport = both(lambda d, lo: d[0] == "resolved" and lo[0] == "resolved")
    first_value = _status_and_value(viewport, dynamic.id)[1]
    assert _status_and_value(viewport, locked.id) == ("resolved", first_value)

    # Another set: the dynamic annotation follows it, the locked one is hidden
    viewport.settings.set_id = last_set
    viewport = both(lambda d, lo: d[1] != first_value and lo[0] == "inactiveSet")
    status, last_value = _status_and_value(viewport, dynamic.id)
    assert status == "resolved"
    assert last_value != first_value
    assert _status_and_value(viewport, locked.id)[0] == "inactiveSet"

    # Unlocking the set shows the locked annotation again, on the active set.
    # The annotation was read before the set changed: editing it must not
    # restore the set it was read with.
    locked.set_ids = None
    viewport = both(lambda d, lo: lo[0] == "resolved")
    assert _status_and_value(viewport, locked.id) == ("resolved", last_value)
    assert viewport.settings.set_id == last_set

    # Locking the component: shown only while the viewport displays it
    locked.result_reference = AnnotationResultReference(name="displacement", component="X")
    viewport = both(lambda d, lo: lo[0] == "inactiveResult")
    assert _status_and_value(viewport, dynamic.id)[0] == "resolved"
    viewport.settings.component_name = "X"
    viewport = both(lambda d, lo: lo[0] == "resolved")
    assert _status_and_value(viewport, locked.id)[0] == "resolved"
