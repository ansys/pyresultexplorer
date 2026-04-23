"""
This example demonstrates how to create a user-defined plot that displays only
the nodes whose total displacement magnitude exceeds a percentage of the
maximum displacement in the model.

It creates a user-defined plot that uses a DPF ``high_pass`` operator to
filter out nodes whose displacement magnitude falls below the threshold,
showing only the regions that meet or exceed the specified percentage of the
maximum displacement.

It covers the following steps:

- Connecting to the PyResultExplorer service
- Creating a workspace and loading a solution
- Defining a server-side script using DPF operators to filter by threshold
- Creating a user-defined plot with a configurable percent threshold option
- Assigning the plot to a viewport

Make sure to update the FILE_PATH and TOKEN variables
with appropriate values before running the example.
"""

import os

from ansys.result_explorer.core import models
from ansys.result_explorer.core.client import Client

FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "data", "multiple_connections.rst")
)
TOKEN = "<insert_your_token_here>"  # noqa E501

# ---------------------------------------------------------------------------
# Plot above threshold script
# ---------------------------------------------------------------------------
# This script is executed server-side by Result Explorer to compute the plot
# data. It extracts displacement, computes the per-node displacement magnitude
# (L2 norm of X/Y/Z components), determines the maximum magnitude across all
# nodes, then applies a DPF ``high_pass`` operator to retain only the nodes
# where the magnitude exceeds ``percent_threshold`` percent of that maximum.

ABOVE_THRESHOLD_SCRIPT = """\
from ansys.dpf import core as dpf
from ansys.result_explorer.server.logger import log
from ansys.result_explorer.server.simulation import SimulationInterface
from ansys.result_explorer.server.plots import PlotDefinition
from ansys.result_explorer.server.simulation.plot_helper import scoping_definition_to_dpf_scoping
from ansys.result_explorer.server.utils import AnnotatedField, UserDefinedContext
from ansys.result_explorer.server.schemas import CustomOptionDefinition

def get_custom_options(
    simulation: SimulationInterface,
    context: UserDefinedContext,
) -> list[CustomOptionDefinition]:
    return [
        CustomOptionDefinition(
            label="Percent Threshold",
            type="float",
            required=False,
            min=0.0,
            max=100.0,
            default_value=85.0,
        )
    ]


def get_custom_plot_data(
    simulation: SimulationInterface,
    definition: PlotDefinition,
    context: UserDefinedContext,
) -> list[AnnotatedField]:
    model = simulation.dpf_model
    server = simulation.server
    mesh = model.metadata.meshed_region

    percent_threshold = float(definition.custom_options.get("Percent Threshold", 50.0))

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

        # Derive the absolute threshold from the percent of the set's maximum magnitude
        min_max_op = dpf.operators.min_max.min_max(field=norm_field, server=server)
        max_val = min_max_op.outputs.field_max().data[0]
        threshold = float(max_val * percent_threshold / 100.0)
        log.info(
            f"Above-threshold plot '{definition.name}': "
            f"set={set_id}, max={max_val:.4e}, "
            f"percent={percent_threshold}%, threshold={threshold:.4e}"
        )

        # Keep only nodes where displacement magnitude >= threshold
        hp_op = dpf.operators.filter.field_high_pass(
            server=server,
            field=norm_field,
            threshold=threshold,
        )
        above_threshold_scoping = hp_op.outputs.field().scoping

        # Rescope the displacement field to the nodes above the threshold
        rescope_op = dpf.operators.scoping.rescope(
            server=server,
            fields=disp_field,
            mesh_scoping=above_threshold_scoping,
        )
        filtered_disp = rescope_op.outputs.fields_as_field()

        # Build a sub-mesh limited to the above-threshold region for correct visualization
        # if len(above_threshold_scoping.ids) > 0:
        #     extract_mesh_op = dpf.operators.mesh.from_scoping(
        #         server=server,
        #         inclusive=1,
        #         mesh=disp_field.meshed_region,
        #         scoping=above_threshold_scoping,
        #     )
        #     filtered_disp.meshed_region = extract_mesh_op.outputs.mesh()
        filtered_disp.meshed_region = mesh

        simulation_time = time_frequencies.data[set_id - 1]
        annotated_fields.append(
            AnnotatedField(
                field=filtered_disp,
                name=f"displacement_above_threshold;{set_id}",
                display_name="Displacement Above Threshold",
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

workspace = rx.create_workspace(name="PyRX Above Threshold Workspace")

sol = rx.create_solution(
    result_provider_name="Local",
    name="PyRX Above Threshold Solution",
    file_path=FILE_PATH,
)
print(f"Created solution: {sol.name}")

# ---------------------------------------------------------------------------
# Create the user-defined above-threshold plot
# ---------------------------------------------------------------------------

ud_plot = sol.create_plot(
    models.PlotDefinitionCreate(
        name="Displacement Above Threshold",
        result_type=models.ResultType.RESULT_TYPE_USER_DEFINED,
        location="unused",
        on_skin=False,
        all_sets=False,
        last_set=True,
        shell_position=models.ShellPosition.SHELL_POSITION_TOP,
        script=ABOVE_THRESHOLD_SCRIPT,
        custom_options={"percent_threshold": models.CustomOptionsValue(float=50.5)},
    )
)

print(f"Created user-defined above-threshold plot: '{ud_plot.name}'")

# ---------------------------------------------------------------------------
# Assign to viewport
# ---------------------------------------------------------------------------

viewport = workspace.assign_view(view=ud_plot, wait=True)

print("Opened above-threshold plot in viewport.")
