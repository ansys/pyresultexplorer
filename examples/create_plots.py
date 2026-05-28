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

"""
This example demonstrates how to create named selections and use them to
create displacement plots in Result Explorer.

It covers the following steps:
- Connecting to the PyResultExplorer service
- Creating a workspace
- Creating a solution from a result file
- Creating named selections based on element IDs
- Creating plot definitions for displacement and velocity using the named selections
- Assigning the plots to viewports in the workspace

Make sure to update the FILE_PATH and TOKEN variables
with appropriate values before running the example.
"""

from ansys.result_explorer.core import models
from ansys.result_explorer.core.client import Client

FILE_PATH = r"D:\Models\mech-post\cylinder_plate\d3plot"
TOKEN = "<insert here>"  # noqa E501

rx = Client.connect_with_token(TOKEN)

workspace = rx.create_workspace(name="PyRX NS Plot Workspace")

sol_name = "PyRX Cylinder Plate"
sol = rx.create_solution(
    result_provider="Local",
    name=sol_name,
    file_path=FILE_PATH,
)
print(f"Created solution: {sol.name}")

if sol.n_sets < 2:
    raise RuntimeError("This example requires at least two result sets/timesteps.")

set_ids = sorted({tf.set_id for tf in sol.time_frequencies})
if len(set_ids) < 2:
    raise RuntimeError("Could not find two distinct set IDs in time frequencies.")

set_id_1, set_id_2 = set_ids[0], set_ids[1]
print(f"Using timesteps (set IDs): {set_id_1}, {set_id_2}")

ns_1 = sol.create_named_selection(
    models.NamedSelectionCreate(
        name="Elements NS 1",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
        element_ids=[models.IdsScoping(values=[1, 2, 3, 4, 5])],
    )
)

ns_2 = sol.create_named_selection(
    models.NamedSelectionCreate(
        name="Elements NS 2",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
        element_ids=[models.IdsScoping(values=[20, 21, 22, 23, 24])],
    )
)

print(f"Created named selections: {ns_1.name}, {ns_2.name}")

existing_view_ids = {v.id for v in sol.views}
plot_1 = sol.create_plot(
    models.PlotDefinitionCreate(
        name=f"Displacement - {ns_1.name} - set {set_id_1}",
        result_type=models.ResultType.RESULT_TYPE_DISPLACEMENT,
        location="Nodal",
        fields=[models.Field(name="displacement", components=["X", "Y", "Z"])],
        named_selection_id=ns_1.id,
        set_ids=[set_id_1],
        all_sets=False,
        last_set=False,
    )
)

existing_view_ids = {v.id for v in sol.views}
plot_2 = sol.create_plot(
    models.PlotDefinitionCreate(
        name=f"Velocity - {ns_2.name} - set {set_id_2}",
        result_type=models.ResultType.RESULT_TYPE_VELOCITY,
        location="Nodal",
        fields=[models.Field(name="velocity", components=["X", "Y", "Z"])],
        named_selection_id=ns_2.id,
        set_ids=[set_id_2],
        all_sets=False,
        last_set=False,
    )
)

left_viewport = workspace.assign_view(view=plot_1, wait=True)
right_viewport = workspace.create_viewport(
    viewport=left_viewport,
    direction=models.ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
)
right_viewport.set_view(plot_2, wait=True)

print("Opened displacement plots in two side-by-side viewports.")
print(f" - Left viewport:  {plot_1.name}")
print(f" - Right viewport: {plot_2.name}")
