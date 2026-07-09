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
.. _save_session_and_workspace_example:

Save sessions and workspace templates
======================================

This example demonstrates how to save Result Explorer sessions and workspace
templates for later reuse:

- **Session saving** to capture the complete state of all workspaces and solutions.
- **Workspace templates** to save individual workspace layouts and configurations.
- **Template export** for sharing and reusing visualization configurations.
- **Multiple workspace management** with different views and layouts.

This example uses a transient structural analysis result to create multiple
workspaces and save them as templates along with the complete session.
"""

# %%
# Import the Result Explorer dependencies.
import tempfile
from pathlib import Path

from ansys.result_explorer.core import launch_result_explorer
from ansys.result_explorer.core.examples import ExampleKeys, get_example_file
from ansys.result_explorer.core.models import ViewType

# %%
# Launch Result Explorer
# ----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# %%
# Create a solution
# ------------------
# Load the transient structural analysis result file.
rst_path = get_example_file(ExampleKeys.RST_CP_TRANSIENT)

sol = rx.create_solution(
    name="Transient Analysis",
    file_path=rst_path,
)
print(f"Created solution: {sol.name}")

# %%
# Retrieve available views
# -------------------------
# Get the available views from the solution for use in workspaces.
views = sol.views
print(f"Available views: {len(views)}")
for v in views:
    print(f"  - {v.name}")

# Get displacement and stress views for the workspaces
disp_view = next((v for v in views if "Displacement" in v.name), None)
stress_view = next((v for v in views if "Stress" in v.name), None)

# %%
# Delete the default workspace
# ----------------------------
# Remove the default "Workspace 1" that is created automatically.
default_workspaces = [ws for ws in rx.list_workspaces() if ws.name == "Workspace 1"]
for ws in default_workspaces:
    rx.delete_workspace(workspace=ws)
    print(f"Deleted default workspace: {ws.name}")

# %%
# Create first workspace with displacement view
# -----------------------------------------------
# Create a workspace and configure it with displacement visualization.
workspace_1 = rx.create_workspace(name="Displacement Workspace")
print(f"\nCreated workspace 1: {workspace_1.name}")

if disp_view:
    viewport_1 = workspace_1.assign_view(view=disp_view, wait=True)
    print(f"  Assigned view: {disp_view.name}")
else:
    print("  No displacement view found, using first available view")
    if views:
        viewport_1 = workspace_1.assign_view(view=views[0], wait=True)

# %%
# Create second workspace with stress view
# ------------------------------------------
# Create another workspace with a different view layout.
workspace_2 = rx.create_workspace(name="Stress Workspace", rows=1, cols=2)
print(f"Created workspace 2: {workspace_2.name} ({len(workspace_2.viewport_ids)} viewports)")

if stress_view:
    viewport_2 = workspace_2.assign_view(view=stress_view, wait=True)
    print(f"  Assigned view: {stress_view.name}")
else:
    print("  No stress view found, using first available view")
    if views:
        viewport_2 = workspace_2.assign_view(view=views[0], wait=True)

# Assign a logs view to the second viewport
logs_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_LOGS), None)
viewport_2 = workspace_2.viewports[1]
viewport_2.set_view(logs_view, wait=True)
print(f"  Assigned view to second viewport: {logs_view.name}")

# %%
# Save session and workspace templates
# ----------------------------------------
# Save the complete session and export each workspace as a template
# to a temporary directory.

temp_dir = Path(tempfile.gettempdir()) / "result_explorer_example"
temp_dir.mkdir(exist_ok=True)

# Save the complete session
session_path = temp_dir / "my_session.rxs"
rx.save_session(str(session_path))
print(f"\nSaved session to: {session_path}")

# Export each workspace as a template
for workspace in rx.list_workspaces():
    template_path = temp_dir / f"{workspace.name}.rxwt"
    workspace.export_as_template(str(template_path))
    print(f"Saved workspace template: {template_path}")

print(f"\nAll files saved to: {temp_dir}")

rx.stop()
