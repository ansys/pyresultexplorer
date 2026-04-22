"""
This example demonstrates how to create a user-defined plot that highlights
displacement "hot spots" — regions where the total displacement magnitude
exceeds a configurable threshold.

Starting from the default displacement plot provided by the solution, it
creates a user-defined plot variant that uses a DPF ``high_pass`` operator to
filter out nodes whose displacement magnitude falls below the threshold,
focusing the visualization on the most heavily displaced regions.

It covers the following steps:

- Connecting to the PyResultExplorer service
- Creating a workspace and loading a solution
- Inspecting the default displacement plot definition
- Defining a server-side script using DPF operators to filter hot spots
- Creating a user-defined plot with a configurable threshold option
- Assigning the plot to a viewport

The "Threshold" custom option can be adjusted interactively in the
Result Explorer UI after the plot is open.

Make sure to update the FILE_PATH and TOKEN variables
with appropriate values before running the example.
"""

import os

from ansys.result_explorer.core import models
from ansys.result_explorer.core.client import Client

FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "data", "multiple_connections.rst")
)
TOKEN = "eyJob3N0IjoibG9jYWxob3N0IiwiaHR0cFBvcnQiOjYwMzA4LCJncnBjUG9ydCI6NjAzMTcsInNlc3Npb25JZCI6IjZlOGEwMDU5LTg3OWYtNGE2Zi04MTZkLTg1OWE2ZmQyNmQ2ZiJ9"  # noqa E501

# ---------------------------------------------------------------------------
# Hot spot plot script
# ---------------------------------------------------------------------------
# This script is executed server-side by Result Explorer to compute the plot
# data. It extracts displacement, computes the per-node displacement magnitude
# (L2 norm of X/Y/Z components), then applies a DPF ``high_pass`` operator to
# retain only the nodes where the magnitude exceeds the user-defined
# "Threshold" custom option.

HOT_SPOT_SCRIPT = """\
from ansys.dpf import core as dpf
from ansys.result_explorer.server.logger import log
from ansys.result_explorer.server.simulation import SimulationInterface
from ansys.result_explorer.server.plots import PlotDefinition
from ansys.result_explorer.server.simulation.plot_helper import scoping_definition_to_dpf_scoping
from ansys.result_explorer.server.utils import AnnotatedField, UserDefinedContext


def get_custom_plot_data(
    simulation: SimulationInterface,
    definition: PlotDefinition,
    context: UserDefinedContext,
) -> list[AnnotatedField]:
    model = simulation.dpf_model
    server = simulation.server
    mesh = model.metadata.meshed_region

    threshold = 1e-5
    log.info(f"Hot spot plot '{definition.name}': threshold={threshold}")

    # Time scoping
    tf = model.metadata.time_freq_support
    if definition.all_sets:
        timeids = range(1, tf.n_sets + 1)
    elif definition.last_set:
        timeids = tf.n_sets
    else:
        timeids = definition.set_ids

    # Mesh scoping
    scoping = scoping_definition_to_dpf_scoping(definition.mesh_scoping, context.mesh_info)

    # Extract displacement
    disp_op = model.results.displacement()
    disp_op.inputs.time_scoping(timeids)
    if scoping is not None:
        if scoping.location == dpf.locations.elemental:
            # Turn elemental scoping into nodal before feeding into displacement op
            transpose_op = dpf.operators.scoping.transpose(
                server=server,
                mesh_scoping=scoping,
                meshed_region=mesh,
            )
            node_scoping = transpose_op.outputs.mesh_scoping_as_scoping()
            disp_op.inputs.mesh_scoping(node_scoping)
        else:
            disp_op.inputs.mesh_scoping(scoping)

    fc_disp = disp_op.outputs.fields_container()
    time_frequencies = fc_disp.time_freq_support.time_frequencies
    annotated_fields = []

    for index, set_id in enumerate(fc_disp.get_time_scoping().ids):
        disp_field = fc_disp[index]

        # Compute per-node displacement magnitude (L2 norm of X, Y, Z)
        norm_op = dpf.operators.math.norm(field=disp_field, server=server)
        norm_field = norm_op.outputs.field()

        # high_pass: keep only nodes where displacement magnitude >= threshold
        hp_op = dpf.operators.filter.field_high_pass(
            server=server,
            field=norm_field,
            threshold=threshold,
        )
        hot_spot_scoping = hp_op.outputs.field().scoping

        # Rescope the displacement field to the hot spot nodes only
        rescope_op = dpf.operators.scoping.rescope(
            server=server,
            fields=disp_field,
            mesh_scoping=hot_spot_scoping,
        )
        filtered_disp = rescope_op.outputs.fields_as_field()

        # Build a sub-mesh limited to the hot spot region for correct visualization
        # if len(hot_spot_scoping.ids) > 0:
        #     extract_mesh_op = dpf.operators.mesh.from_scoping(
        #         server=server,
        #         inclusive=1,
        #         mesh=disp_field.meshed_region,
        #         scoping=hot_spot_scoping,
        #     )
        #     filtered_disp.meshed_region = extract_mesh_op.outputs.mesh()
        filtered_disp.meshed_region = mesh

        simulation_time = time_frequencies.data[set_id - 1]
        annotated_fields.append(
            AnnotatedField(
                field=filtered_disp,
                name=f"displacement_hot_spots;{set_id}",
                display_name="Displacement Hot Spots",
                set_id=set_id,
                time_freq=simulation_time,
                time_freq_unit=simulation.time_freq_support.time_frequencies.unit,
            )
        )

    return annotated_fields


"""

# ---------------------------------------------------------------------------
# Connect and set up workspace / solution
# ---------------------------------------------------------------------------

rx = Client.connect_with_token(TOKEN)

workspace = rx.create_workspace(name="PyRX Hot Spot Workspace")

sol = rx.create_solution(
    result_provider_name="Local",
    name="PyRX Hot Spot Solution",
    file_path=FILE_PATH,
)
print(f"Created solution: {sol.name}")

# ---------------------------------------------------------------------------
# Create the user-defined hot spot plot
# ---------------------------------------------------------------------------
# The initial threshold is set here via custom_options. The value is visible
# and adjustable in the Result Explorer UI under the plot's custom options
# panel once the viewport is open.

hot_spot_view = sol.create_plot(
    models.PlotDefinitionCreate(
        name="Displacement Hot Spots",
        result_type=models.ResultType.RESULT_TYPE_USER_DEFINED,
        location="unused",
        on_skin=False,
        all_sets=False,
        last_set=True,
        shell_position=models.ShellPosition.SHELL_POSITION_TOP,
        script=HOT_SPOT_SCRIPT,
    )
)

print(f"Created user-defined hot spot plot: '{hot_spot_view.name}'")

# ---------------------------------------------------------------------------
# Assign to viewport
# ---------------------------------------------------------------------------

viewport = workspace.assign_view(view=hot_spot_view, wait=True)

print("Opened hot spot plot in viewport.")
print("Adjust the 'Threshold' custom option in the Result Explorer UI to control sensitivity.")
