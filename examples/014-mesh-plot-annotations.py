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

"""
.. _mesh_plot_annotations_example:

Annotate mesh and plot viewports
================================

This example shows how to add annotations to 3D viewports with
``viewport.annotations``, and read them back once Result Explorer resolves
them in the scene:

- **Mesh annotations** anchored to a node, showing its location.
- **Plot annotations** showing the result value at the node, either
  dynamic (following the displayed result) or locked to a result,
  component, or set.
- **Annotation edits** such as the note, the card placement, and the
  properties shown on the card.

"""

# %%
# Import dependencies
import time

from ansys.result_explorer.core import (
    AnnotationAnchor,
    AnnotationPlacement,
    AnnotationResultReference,
    AnnotationTarget,
    AnnotationTargetKind,
    Viewport,
    launch_result_explorer,
)
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)
from ansys.result_explorer.core.models import ViewportDirection

# %%
# Launch Result Explorer and load data
# ------------------------------------
# Start a Result Explorer instance and create a solution.
rx = launch_result_explorer()

rst_path = get_example_file(ExampleKeys.RST_MULTIPLE_CONNECTIONS)
sol = rx.create_solution(name="Annotations Example Solution", file_path=rst_path)
print(f"Solution created: {sol}")

workspace = rx.create_workspace(name="Annotations Example Workspace")

# %%
# Define a helper to read resolved annotations
# --------------------------------------------
# Result Explorer resolves annotations in the scene after rendering. This
# helper fetches the viewport again until its annotations are resolved.


def wait_for_annotations(viewport: Viewport, count: int, timeout: float = 30.0) -> Viewport:
    """Return the viewport once exactly ``count`` annotations are resolved."""
    deadline = time.monotonic() + timeout
    while True:
        viewport = next(v for v in rx.get_workspace(workspace.id).viewports if v.id == viewport.id)
        resolved = sum(a.status == "resolved" for a in viewport.annotations)
        if resolved == count or time.monotonic() > deadline:
            return viewport
        time.sleep(1)


# %%
# Find the body to annotate
# -------------------------
# Bodies carry the mesh properties they were split by, such as the material
# ID in the ``mat`` label. Find the body made of material 3.
body = next(b for b in sol.bodies if b.labels.get("mat") == "3")
print(f"Body {body.id} ({body.name}) has labels {dict(body.labels)}")

# %%
# Annotate the mesh
# -----------------
# Assign the mesh view to the viewport and anchor an annotation to a node.
# The target needs the node ID and the bodies to look it up in. Node 21 lies
# on the body made of material 3; anchoring to this body only shows the
# location and results of the node on this body.
mesh_viewport = workspace.assign_view(view=sol.mesh_view, wait=True)

node = AnnotationTarget(kind=AnnotationTargetKind.node, id=21, body_ids=(body.id,))
mesh_annotation = mesh_viewport.annotations.add(
    AnnotationAnchor(target=node), note="Monitored node"
)
print(f"Added {mesh_annotation}")

# %%
# By default, a mesh annotation card shows the node ID, the body, its
# location, and the note. Hide the location to make the card smaller.
mesh_annotation.property_visibility.mesh_location = False
print(mesh_annotation.property_visibility)

# %%
# Once resolved, the annotation also gives the node location.
mesh_viewport = wait_for_annotations(mesh_viewport, count=1)
mesh_annotation = mesh_viewport.annotations[mesh_annotation.id]
print(f"Status: {mesh_annotation.status}, mesh location: {mesh_annotation.mesh_location}")
mesh_viewport.save_snapshot(
    file_path="014-mesh-plot-annotations-mesh.png", settings=get_example_snapshot_settings()
)

# %%
# Annotate a plot
# ---------------
# Split the viewport and show the displacement plot in the new viewport.
plot_view = next(v for v in sol.plot_views if "Displacement" in v.name)
plot_viewport = workspace.create_viewport(
    mesh_viewport, ViewportDirection.VIEWPORT_DIRECTION_RIGHT
).set_view(plot_view, wait=True)

# %%
# An empty result reference makes Result Explorer look up the value of the
# displayed result at the node. The annotation is dynamic: it follows the
# result, the component, and the set displayed in the viewport.
plot_annotation = plot_viewport.annotations.add(
    AnnotationAnchor(target=node),
    note="Monitored node",
    result_reference=AnnotationResultReference(),
)
plot_annotation.property_visibility.result_name = True
plot_annotation.property_visibility.result_component = True

plot_viewport = wait_for_annotations(plot_viewport, count=1)
plot_annotation = plot_viewport.annotations[plot_annotation.id]
print(f"Status: {plot_annotation.status}, result: {plot_annotation.result}")
print(f"Deformed location: {plot_annotation.deformed_location}")
plot_viewport.save_snapshot(
    file_path="014-mesh-plot-annotations-plot.png", settings=get_example_snapshot_settings()
)

# %%
# Lock annotations
# ----------------
# A locked annotation shows a given result, component, or set, and is
# shown only while the viewport displays them. Lock a second annotation to
# the X component of the displacement: it stays hidden while the viewport
# displays the magnitude. The component ``""`` stands for the magnitude, and
# ``set_ids`` locks the sets in the same way.
result_name = str(plot_viewport.settings.result)
x_annotation = plot_viewport.annotations.add(
    AnnotationAnchor(target=node),
    note="Monitored node, X",
    result_reference=AnnotationResultReference(name=result_name, component="X"),
    set_ids=[int(plot_viewport.settings.set_id or 1)],
)
x_annotation.property_visibility.result_component = True
print(f"Locked to {x_annotation.result_reference}, sets {x_annotation.set_ids}")

# %%
# Display the X component: the dynamic annotation now shows the X value,
# and the locked annotation is shown too.
plot_viewport.settings.component_name = "X"
plot_viewport = wait_for_annotations(plot_viewport, count=2)
for annotation in plot_viewport.annotations:
    print(f"{annotation.note!r}: {annotation.status}, {annotation.result}")

# %%
# Display the magnitude again: the locked annotation is hidden, with the
# reason in its status.
plot_viewport.settings.component_name = "Magnitude"
plot_viewport = wait_for_annotations(plot_viewport, count=1)
for annotation in plot_viewport.annotations:
    print(f"{annotation.note!r}: {annotation.status}")

# %%
# Setting the reference fields and the sets to None makes an annotation
# dynamic again.
x_annotation.result_reference = AnnotationResultReference()
x_annotation.set_ids = None

# %%
# Edit annotations
# ----------------
# The anchor is fixed once the annotation is created. The note, the
# visibility, the placement, and the card properties are editable. Batch
# the edits to apply them in a single call.
with plot_viewport.update_settings():
    plot_annotation.note = "Monitored node, pinned"
    plot_annotation.placement = AnnotationPlacement.screen_pinned
    plot_annotation.card_screen_location = (1.0, 0.25)

for annotation in plot_viewport.annotations:
    print(f"{annotation.note!r}: {annotation.placement}, {annotation.card_screen_location}")
plot_viewport.save_snapshot(
    file_path="014-mesh-plot-annotations-pinned.png", settings=get_example_snapshot_settings()
)

# %%
# Remove annotations
# ------------------
# Remove an annotation by ID, or all of them at once.
mesh_viewport.annotations.remove(mesh_annotation.id)
plot_viewport.annotations.clear()
print(f"Remaining annotations: {len(plot_viewport.annotations)}")

rx.stop()
