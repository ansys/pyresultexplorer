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
.. _create_and_modify_charts_example:

Create and Modify Charts
========================

This example demonstrates how to create and work with charts in Result Explorer:

- **Chart creation** using the native Python ``ChartDefinition`` and ``ChartResult``
  objects to define result series with filters and field selections.
- **Multi-result charts** combining equivalent stress, temperature, and contact
  pressure results in a single chart.
- **Chart display options** to control legend visibility, table display, and
  active series selection.
- **Chart updates** to add or modify result series in an existing chart.
- **Snapshot capture** to save chart visualizations as images.

This example uses a transient analysis with multiple time steps, which is
well-suited for charts that plot results over time. Print the solution object
to inspect available results and configurable chart types.
"""

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import launch_result_explorer
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)
from ansys.result_explorer.core.objects.chart_definition import (
    ChartDefinition,
    ChartResult,
    Filter,
)
from ansys.result_explorer.core.objects.plot_definition import (
    Field,
    ResultFieldName,
    ResultType,
    ShellPosition,
)

# %%
# Launch Result Explorer
# ----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# %%
# Load Example Data
# -----------------
# Create a solution from a transient analysis result file with multiple
# time steps — ideal for charts that plot how results evolve over time.
# Print the solution to inspect available results and configurable chart types.
rst_path = get_example_file(ExampleKeys.RST_CP_TRANSIENT)

sol = rx.create_solution(
    name="Chart Example Solution",
    file_path=rst_path,
)
print(f"Created solution: {sol.name}")
print(f"  Time steps: {sol.n_sets}")
print(sol)

# %%
# Create a Workspace
# -------------------
workspace = rx.create_workspace(name="Chart Example Workspace")

# %%
# Create a Chart
# ---------------
# Build a chart that plots equivalent von Mises stress, temperature, and
# contact pressure over all time steps.  ``Filter.max`` keeps only the
# maximum value per step so the chart shows peak results.
chart = sol.create_chart(
    ChartDefinition(
        name="Stress, Temperature & Contact Pressure Over Time",
        all_sets=True,
        results=[
            ChartResult(
                result_type=ResultType.stress,
                name="Stress",
                location="Nodal",
                fields=[Field(ResultFieldName.equivalent_von_mises_stress)],
                filters=[Filter.max],
                shell_position=ShellPosition.all,
            ),
            ChartResult(
                result_type=ResultType.temperature,
                name="Temperature",
                location="Nodal",
                fields=[Field(ResultFieldName.temperature)],
                filters=[Filter.max],
            ),
            ChartResult(
                result_type=ResultType.contact,
                name="Contact",
                location="Nodal",
                fields=[Field(ResultFieldName.contact_pressure)],
                filters=[Filter.max],
            ),
        ],
    )
)

print(f"\nCreated chart view: '{chart.name}'")
print(f"Chart definition id: {chart.definition.id}")

# %%
# Assign the Chart to a Viewport
# --------------------------------
# Assign the chart view to a viewport and wait for it to finish rendering.
viewport = workspace.assign_view(view=chart, wait=True)
print(f"\nViewport assigned: {viewport.id}")

# %%
# Inspect Chart Display Options
# ------------------------------
# Read the available series and chart names provided by the server after
# rendering, then print them so you can reference them by name.
opts = viewport.display_options

print(f"\nAvailable series: {opts.series_names}")
print(f"Available charts: {opts.chart_names}")
print(f"Active series:    {opts.active_series}")

# %%
# Configure Display Options
# --------------------------
# Enable the legend and show the data table beneath the chart.
opts.show_legend = True
opts.show_table = True

# %%
# Select Active Series
# ---------------------
# Restrict the viewport to display only the stress series so temperature
# and contact pressure are hidden.
if opts.series_names:
    opts.active_series = opts.series_names[1:2]
    print(f"\nActive series (stress only): {opts.active_series}")

viewport.save_snapshot(
    file_path="030-chart-stress-only.png",
    settings=get_example_snapshot_settings(),
)

# %%
# Restore All Series
# -------------------
# Re-activate all available series.
opts.active_series = opts.series_names[1:]

viewport.save_snapshot(
    file_path="030-chart-with-all-quantities.png",
    settings=get_example_snapshot_settings(),
)

# %%
# List Charts in the Solution
# ----------------------------
# ``sol.charts`` now returns a list of native ``ChartDefinition`` objects.
print("\nCharts in solution:")
for c in sol.charts:
    print(f"  {c.name!r} — {len(c.results)} result series")

rx.stop()
