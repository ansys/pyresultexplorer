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
.. _workspace_layout_example:

Create Workspace Grid Layouts
==========================================

This example demonstrates how to create and manage workspace layouts with
various grid configurations in PyResultExplorer:

- **Workspace creation** with custom grid dimensions using rows and columns.
- **Grid layout configurations** from 1x1 to 3x3 grid arrangements.
- **Viewport sizing and positioning** in grid-based layouts.

This example showcases the flexibility of Result Explorer's workspace layout
system for organizing and visualizing multiple result sets simultaneously.
"""

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import launch_result_explorer
from ansys.result_explorer.core.examples import ExampleKeys, get_example_file

# %%
# Launch Result Explorer
# ----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# Create a solution
rst_path = get_example_file(ExampleKeys.RST_MULTIPLE_CONNECTIONS)
sol = rx.create_solution(
    name="Example Solution",
    file_path=rst_path,
)

# %%
# Create Workspace Grid Layouts
# ------------------------------
# Create workspaces with various grid configurations from 1x1 to 3x3 and
# inspect the viewports in each layout.

for r in range(1, 4):
    for c in range(1, 4):
        workspace = rx.create_workspace(name=f"{c}x{r} Grid Workspace", rows=r, cols=c)
        print(f"Created workspace: {workspace.name} (id: {workspace.id})")
        viewports = workspace.viewports
        print(f"Viewport count: {len(viewports)}")
        print("-" * 40)
