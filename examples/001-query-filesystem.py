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
.. _query_filesystem_example:

Query the File System and Access Solution Data
===============================================

This example demonstrates how to interact with Result Explorer's file system
and solution management capabilities:

- **File system queries** allow you to browse and explore the directory structure
  of result data using the ``rx.ls()`` method.
- **Solution creation** enables you to load result files and organize simulation
  data for analysis and visualization.
- **Solution data access** provides methods to retrieve and examine solver output
  through the solution entity.

This example uses transient structural analysis results for demonstration.
"""

# %%
# Launch Result Explorer
# ----------------------

# Import dependencies.

from ansys.result_explorer.core import launch_result_explorer, models
from ansys.result_explorer.core.examples import ExampleKeys, get_example_file

# Start a Result Explorer instance.
rx = launch_result_explorer()

# Get the path to the example result file. This is a transient structural
# analysis result in RST format.
rst_path = get_example_file(ExampleKeys.RST_CP_TRANSIENT)

# %%
# Query the File System
# ---------------------
# List the contents of the directory containing the result file.
# Define a helper function to pretty-print the file system structure.


def pretty_print_fs_items(items: list[models.FSItem], indent: int = 0) -> None:
    """Pretty-print file system items with hierarchical formatting."""
    prefix = " " * indent
    for item in items:
        if item.is_file:
            print(f"{prefix}- {item.name}")
        else:
            print(f"{prefix}- {item.name}/")
            if item.content:
                pretty_print_fs_items(list(item.content), indent=indent + 2)


# %%
# Query the directory at depth 0 to see the top-level contents.
content = rx.ls(path=rst_path.parent, depth=0)
pretty_print_fs_items(content)

# %%
# Create a Solution
# -----------------
# Create a solution from the result file. A solution is a container for result
# data that allows you to query and visualize the simulation results.
solution = rx.create_solution(
    name="Test Solution",
    file_path=rst_path,
)

# %%
# Access Solver Output Through Solution
# ----------------------------------------
# Retrieve solver text output files from the solution. In this case, we access
# the ``file.gst`` file, which contains transient convergence information.
out_file = next((f for f in solution.solver_text_outputs if f.name == "file.gst"), None)
assert out_file is not None, "file.gst not found in solver text outputs"

# %%
# Get the content of the solver output file through the solution entity.
gst_via_solution = solution.get_solver_out_content(out_file)
print("\nContent of file.gst accessed via solution entity:")
print(gst_via_solution)
