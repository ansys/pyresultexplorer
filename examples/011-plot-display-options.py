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

import os
import time

from ansys.result_explorer.core import (
    PlotDisplayOptions,
    PlotView,
    launch_result_explorer,
)
from ansys.result_explorer.core.models import ViewType

# Path to cp_trans test data (contact + transient analysis)
FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "data", "cp_trans", "file.rst")
)

rx = launch_result_explorer()

# Create a solution from the transient contact analysis
sol = rx.create_solution(
    name="Contact Transient Analysis",
    file_path=FILE_PATH,
)
print(f"Created solution:\n{sol}")

# Find plot view
views = sol.views
disp_view: PlotView = next(
    (v for v in views if v.type == ViewType.VIEW_TYPE_PLOT and "Displacement" in v.name), None
)

assert disp_view is not None, "Displacement view not found in solution"

disp_view.definition.all_sets = True
disp_view.definition.last_set = False
sol.update_plot(disp_view.definition)

print(f"Found displacement view: {disp_view.name}")

# Create a workspace with a 2x1 grid layout
workspace = rx.create_workspace(name="Plot Viewports")
print(f"Created workspace with {len(workspace.viewport_ids)} viewports (2x1 grid)")

# Assign displacement view to top viewport
disp_viewport = workspace.viewports[0]
disp_viewport.set_view(disp_view, wait=True)

# Configure displacement plot display options
with disp_viewport.update_display_options() as disp_opts:
    assert isinstance(disp_opts, PlotDisplayOptions)
    disp_opts.result_options.use_global_min_max = False
    disp_opts.result_options.component_index = 0
    disp_opts.result_options.deformation_scale = 2
    disp_opts.show_mesh_edges = True


# Animate through all time steps
time_frequencies = sol.time_frequencies
print(f"Animating over {len(time_frequencies)} time steps...")
for i, tf in enumerate(time_frequencies):
    print(f"  Step {i}: set_id={tf.set_id}, value={tf.value}")
    opts = disp_viewport.display_options
    # Setting this property auto-commits to the server
    opts.result_options.set_id = tf.set_id

    meta = disp_viewport.metadata
    for extreme in [meta.active_result.min, meta.active_result.max]:
        print(f"    entity={extreme.entity_id}, value={extreme.value}, pos={extreme.position}")

    time.sleep(0.2)
