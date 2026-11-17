# Annotations and hot spots (POC)

Status: proof of concept, on branch `feat/annotations-hotspots`.

## Goal

Expose Result Explorer annotations and hot spots in PyResultExplorer:

1. Annotation definitions stored in the viewport settings, fully readable, with
   the same edits the UI allows.
2. Hot spots, which the web UI exposes as resolved annotations in the viewport
   metadata, as read-only objects.
3. Editing a hot spot by copying it into the viewport settings annotations. Only
   the presentation is editable (note, visibility, placement, card location,
   property visibility). The anchor, sets and result values stay read-only.
4. The hot spot definition of a plot definition (detection on the server).
5. The viewport display options that filter the detected hot spots.

## Background: how the web UI stores annotations

The scripting API has no annotation messages. Annotations travel in the
generic viewport settings and metadata (`google.protobuf.Struct` values):

| Location | Key | Content |
| --- | --- | --- |
| `Viewport.settings` | `annotations` | `AnnotationDefinition[]`: user annotations and edited copies of graphics annotations |
| `Viewport.settings` | `hotSpotsMaxNumber` | maximum number of hot spots per set (and per body when by entity) |
| `Viewport.settings` | `hotSpotsByEntity` | whether the maximum applies per body |
| `Viewport.settings` | `hotSpotsSeparationDistance` | minimum distance between two hot spots |
| `Viewport.settings` | `hotSpotsThresholdRange` | `{low?, high?}` value range of the hot spots |
| `Viewport.metadata` | `resolvedAnnotations` | `ResolvedSceneAnnotation[]`: annotations shown in the scene, resolved against the displayed data |

The server computes hot spot candidates when the plot definition has a
`hot_spot_definition`. They are delivered with the graphics data as
annotations with `group == "hotspots"` and `source == "graphics"`. The web UI
filters them with the display options above and lists the remaining ones in
`resolvedAnnotations`.

A graphics annotation is edited by saving a copy with the same `id` (and
`source == "graphics"`) in the `annotations` setting. The web UI merges the
copy into the graphics annotation: the anchor, sets and result come from the
data, and the note, placement, card location, visibility and property
visibility come from the copy. A copy without a matching graphics annotation
stays dormant.

Reference sources in `result-explorer-web`
(`projects/snps-ansys-internal/...`):

- `mbu-three-d/src/lib/annotations/annotation-definition.ts`
- `mbu-three-d/src/lib/annotations/annotation-resolution.ts`
- `mbu-three-d/src/lib/annotations/annotation-graphics.ts`
- `result-explorer/src/lib/util/hot-spots.ts`

## Python API

### Plot definition

```python
from ansys.result_explorer.core import HotSpotDefinition, HotSpotKind

definition = plot.definition
definition.hot_spot_definition = HotSpotDefinition(kind=HotSpotKind.maximum, num_hotspots=5)
plot = solution.update_plot(definition)
```

`HotSpotDefinition` (`kind`, `num_hotspots`, `separation_distance`,
`threshold_low`, `threshold_high`) maps to the `server_models.HotSpotDefinition`
message, added in ansys/ansys-api-result-explorer#84. `None` disables detection.

### Hot spot display options

New `PlotViewportSettings` properties. They follow the existing settings
pattern: wrapped value on read, auto-commit on write, batching through
`Viewport.update_settings()`.

| Property | Setting key | Type |
| --- | --- | --- |
| `hot_spots_max_number` | `hotSpotsMaxNumber` | `IntSetting \| None` |
| `hot_spots_by_entity` | `hotSpotsByEntity` | `BoolSetting \| None` |
| `hot_spots_separation_distance` | `hotSpotsSeparationDistance` | `FloatSetting \| None` |
| `hot_spots_threshold_range` | `hotSpotsThresholdRange` | `TupleSetting[float \| None] \| None`, as `(low, high)` |

Assigning `None` clears the criterion (verified against the web UI). A `None`
bound of the threshold range is open. When a plot with a hot spot definition
is shown, the web UI initializes `hotSpotsMaxNumber` from `num_hotspots`.

### Annotations and hot spots on the viewport

Annotations and hot spots are edited on the viewport, which combines the
stored definitions (settings) with their resolution in the scene (metadata):

| Accessor | Viewports | Items |
| --- | --- | --- |
| `viewport.annotations` | plot and mesh | `ViewportAnnotation` in a `ViewportAnnotations` collection (`add`, `remove`, `clear`, by index or ID) |
| `viewport.hot_spots` | plot | `HotSpot` list |

Other viewports raise `TypeError`.

```python
annotation = viewport.annotations.add(
    AnnotationAnchor(target=AnnotationTarget(AnnotationTargetKind.node, 21, ("9",))),
    note="Monitored node",
    result_reference=AnnotationResultReference(name="displacement"),
)
annotation.note = "Updated"
annotation.status, annotation.result  # resolution in the scene

hot_spot = viewport.hot_spots[0]
hot_spot.result.value, hot_spot.mesh_location  # from the data, read-only
with viewport.update_settings():
    hot_spot.note = "Highest stress"  # stores an edited copy
    hot_spot.property_visibility.result_name = True
hot_spot.is_edited  # True
hot_spot.reset()  # removes the copy, restoring the original presentation
```

Shared attributes of `ViewportAnnotation` and `HotSpot`:

| Attribute | Editable | Notes |
| --- | --- | --- |
| `id`, `set_ids` | no | |
| `anchor` | no | frozen `AnnotationAnchor` (`position`, `target`, `displacement`) |
| `result_reference` | no | frozen `AnnotationResultReference` (`name`, `component`, `value`) |
| `note` | yes | |
| `visibility` | yes | |
| `placement` | yes | `AnnotationPlacement.follow_scene` or `screen_pinned` |
| `card_screen_location` | yes | `(x, y)` of a pinned card, as fractions of the viewport from `(0, 0)` top left to `(1, 1)` bottom right |
| `property_visibility` | yes | `AnnotationPropertyVisibility`, 8 flags |
| `status` | no | `AnnotationStatus` (`resolved`, `pending`, `inactiveSet`, ...), or `None` until resolved |
| `body_hidden` | no | all bodies of the anchor are hidden |
| `mesh_location`, `deformed_location`, `scene_location` | no | `(x, y, z)` or `None` |
| `result` | no | `AnnotationResult` (`name`, `component`, `value`, `unit`) or `None` |

`HotSpot` adds `is_edited` and `reset()`. A hot spot is edited through a copy
with the same `id` and `source == "graphics"` in the `annotations` setting,
which the first edit creates. `viewport.annotations` lists user annotations
only, not these copies.

Design rules:

- **Live lookup.** Items hold an ID, not a copy of the definition. Each read
  and write looks the definition up in the viewport's current settings, so
  two items, or an item and a direct settings edit, never overwrite each
  other. Reading a removed user annotation raises `LookupError`.
- **Batching.** Inside `viewport.update_settings()`, edits go to the batched
  settings and are applied with them in a single call.
- **Freshness.** Presentation fields of hot spots read the settings, so edits
  are visible immediately. Resolution and data fields reflect the metadata
  when the viewport was last read; the web UI publishes it after rendering.
  The hot spot list is a snapshot: editing a hot spot that a filter has since
  removed stores a dormant copy, as in the web UI.

### Read-only layers

The stored and resolved data stays available read-only:

- `ThreeDViewportSettings.annotations`: list of `Annotation`, the stored
  definitions, including edited hot spot copies.
- `ThreeDViewportMetadata.resolved_annotations` (plot and mesh) and
  `PlotViewportMetadata.hot_spots` (plot): lists of `ResolvedAnnotation`.
  Writing to them raises `AttributeError`.

## Implementation

- `objects/annotation.py`: annotation value types, the read-only
  `Annotation` and `ResolvedAnnotation`, and the viewport-level
  `ViewportAnnotation`, `HotSpot` and `ViewportAnnotations`.
- `objects/plot_definition.py`: `HotSpotKind`, `HotSpotDefinition` and the
  proto conversions.
- `objects/viewport.py`: `Viewport.annotations` and `Viewport.hot_spots`,
  batch tracking in `update_settings()`, `ThreeDViewportMetadata`, the
  read-only `annotations` on `ThreeDViewportSettings`, and the hot spot
  options on `PlotViewportSettings`.

## Examples

- `examples/014-mesh-plot-annotations.py`: user annotations on mesh and plot
  viewports, resolved locations and values, edits and removal.
- `examples/015-hotspots.py`: hot spot detection, inspection, filters, edits,
  and detection of the lowest values.

## Validation

- Unit tests (`tests/test_annotations.py`, no server): plot definition round
  trip, resolved hot spot parsing and read-only rules, hot spot edit copies
  and reset, user annotations with live lookup and resolution, display
  options serialization.
- Integration tests: enable hot spots on an equivalent stress plot, limit them
  and edit one in a batch, check the edit in the resolved metadata, and reset
  it (`test_hot_spots`); annotations on a mesh viewport and the view type
  errors (`test_annotations_and_hot_spots_by_view_type`).

## Dependencies and known issues

- Requires `ansys-api-result-explorer` with ansys/ansys-api-result-explorer#84
  (pinned) and the matching gateway client in the web UI
  (`@snps-ansys-internal/result-explorer-gateway-api` 0.0.24).
- The web UI's enum schema generator did not map nested enums, so the server
  rejected `hot_spot_definition.kind`. Fixed in
  snps-ansys-internal/result-explorer-web#2173.
- Resolved annotations are published by the web UI after rendering, so they
  are only available once the viewport is rendered. Tests poll for them.
- Updating a plot definition from scripting didn't reload the data of
  viewports that already show the plot: the `UpdatePlotDefinition` handler
  called `SolutionService.editPlot` instead of
  `AppCommandsService.editPlotView`. Fixed in
  snps-ansys-internal/result-explorer-web#2173, covered by
  `test_hot_spots_refresh_on_plot_update` and
  `test_plot_update_refreshes_open_viewport`.
- Annotations, including hot spots, are behind the web UI `enableAnnotations`
  setting, which is off by default. Without it, `resolvedAnnotations` stays
  empty. The test fixture enables it.
- `ViewportAnnotations.add` stores the same default property visibility as
  the web UI: node ID, body, location and note without a result reference,
  result value and note with one.
- Annotation definitions are typed only in TypeScript. An `annotation.proto`
  exists on the `feat/annotations` branch of `ansys-api-result-explorer` but
  the scripting API doesn't use it. If annotations become API messages, the
  proxies can switch to them without changing the Python API.

## Possible follow-ups

### Group the scene resolution under a sub-object

`ViewportAnnotation` and `HotSpot` combine the definition and its resolution
in the scene in one object, with the resolution fields (`status`,
`body_hidden`, `mesh_location`, `deformed_location`, `scene_location`,
`result`) flat on it. Combining them is right: users think of one
annotation, and the web UI's `ResolvedSceneAnnotation` also wraps its
definition. Flattening hides that the two halves behave differently:

| | Definition | Resolution |
| --- | --- | --- |
| Owned by | the user (settings) | the web UI, after rendering (metadata) |
| Freshness | live, edits visible immediately | snapshot of the last viewport read |
| Depends on | the annotation only | the annotation and the scene: set, result, shown bodies |
| Availability | always | `None` until rendered |

Proposal: move the resolution fields to an `AnnotationResolution` value
object, `annotation.resolution`, which is `None` until the scene is rendered:

```python
annotation.note  # definition, live
annotation.resolution.status  # scene, as last read
annotation.resolution.result.value
hot_spot.resolution.mesh_location
```

This makes the freshness boundary explicit, replaces one `None` check per
field with a single one, and avoids `result` sitting next to
`result_reference`. For hot spots, whose value comes with the data in
`result_reference.value`, a `HotSpot.value` shortcut could keep the common
case short.