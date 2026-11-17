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
    AnnotationStatus,
    AnnotationTarget,
    AnnotationTargetKind,
    Client,
    Field,
    HotSpotDefinition,
    HotSpotKind,
    PlotDefinition,
    PlotViewportMetadata,
    PlotViewportSettings,
    ResolvedAnnotation,
    ResultFieldName,
    ResultType,
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
    assert hot_spot.status == AnnotationStatus.resolved
    assert hot_spot.anchor.target == AnnotationTarget(AnnotationTargetKind.node, 12, ("4",))
    assert hot_spot.deformed_location == (1.0, 2.0, 3.5)
    assert hot_spot.result is not None
    assert hot_spot.result.unit == "Pa"
    assert hot_spot.result_reference == AnnotationResultReference("stress", "", 250.0)

    with pytest.raises(AttributeError, match="read-only"):
        hot_spot.note = "edited"
    with pytest.raises(AttributeError, match="read-only"):
        hot_spot.property_visibility.result_name = True
    with pytest.raises(AttributeError):
        hot_spot.anchor = AnnotationAnchor()  # type: ignore[misc]


def test_hot_spot_edit_copy_in_settings():
    opts = _offline_settings({"annotations": None})
    hot_spot = ResolvedAnnotation(HOT_SPOT)

    edit = opts.annotations.add_hot_spot(hot_spot)
    edit.note = "Max stress"
    edit.property_visibility.result_name = True

    assert opts.annotations.add_hot_spot(hot_spot).note == "Max stress"
    (stored,) = _round_trip(opts)["annotations"]
    assert stored["id"] == "max:1"
    assert stored["source"] == "graphics"
    assert stored["note"] == "Max stress"
    assert stored["propertyVisibility"]["resultName"] is True
    assert stored["resultReference"]["value"] == 250.0

    opts.annotations.remove(edit)
    assert "max:1" not in opts.annotations


def test_user_annotations_in_settings():
    opts = _offline_settings({})
    anchor = AnnotationAnchor(position=(0.0, 0.0, 0.1))

    annotation = opts.annotations.add(anchor, note="Origin", id="a1")
    assert annotation.property_visibility.mesh_location is True
    assert annotation.property_visibility.result_value is False
    with_result = opts.annotations.add(anchor, result_reference=AnnotationResultReference("s"))
    assert with_result.property_visibility.result_value is True
    assert with_result.property_visibility.mesh_location is False
    opts.annotations.remove(with_result)

    annotation.placement = AnnotationPlacement.screen_pinned
    annotation.card_screen_location = (0.5, 1.0)

    with pytest.raises(ValueError, match="between 0 and 1"):
        annotation.card_screen_location = (10.0, 20.0)

    with pytest.raises(ValueError, match="already exists"):
        opts.annotations.add(anchor, id="a1")

    restored = PlotViewportSettings._from_pb(opts._to_pb(), client=NO_CLIENT).annotations
    assert restored["a1"].anchor == anchor
    assert restored["a1"].placement == AnnotationPlacement.screen_pinned
    assert restored["a1"].card_screen_location == (0.5, 1.0)

    opts.annotations.clear()
    assert _round_trip(opts)["annotations"] == []


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


def _hot_spots(viewport: Viewport) -> list[ResolvedAnnotation]:
    metadata = viewport.metadata
    assert isinstance(metadata, PlotViewportMetadata)
    return metadata.hot_spots


def _note_of(viewport: Viewport, annotation_id: str) -> str | None:
    return next((h.note for h in _hot_spots(viewport) if h.id == annotation_id), None)


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

    viewport.settings.hot_spots_max_number = 2
    hot_spot = hot_spots[0]

    edit = viewport.settings.annotations.add_hot_spot(hot_spot)
    edit.note = "Max stress"

    assert viewport.settings.hot_spots_max_number == 2
    assert viewport.settings.annotations[hot_spot.id].note == "Max stress"
    viewport = _wait_for_metadata(
        rx, workspace.id, viewport.id, lambda v: _note_of(v, hot_spot.id) == "Max stress"
    )
    edited = next(h for h in _hot_spots(viewport) if h.id == hot_spot.id)
    assert edited.note == "Max stress"
    assert edited.result_reference == hot_spot.result_reference


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
