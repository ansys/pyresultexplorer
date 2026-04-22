"""Tests for the plot-above-threshold user-defined plot example."""

import logging
from collections.abc import Generator

import pytest

from ansys.result_explorer.core import Client, Solution, models

log = logging.getLogger(__name__)

# Simplified server-side script for testing: computes displacement magnitude
# for the last set and keeps only nodes above 50% of the maximum.
ABOVE_THRESHOLD_SCRIPT = """\
from ansys.dpf import core as dpf
from ansys.result_explorer.server.simulation import SimulationInterface
from ansys.result_explorer.server.plots import PlotDefinition
from ansys.result_explorer.server.utils import AnnotatedField, UserDefinedContext


def get_custom_plot_data(
    simulation: SimulationInterface,
    definition: PlotDefinition,
    context: UserDefinedContext,
) -> list[AnnotatedField]:
    model = simulation.dpf_model
    server = simulation.server

    percent_threshold = 50.0

    tf = model.metadata.time_freq_support
    set_id = tf.n_sets

    disp_op = model.results.displacement()
    disp_op.inputs.time_scoping([set_id])
    fc_disp = disp_op.outputs.fields_container()
    disp_field = fc_disp[0]

    norm_op = dpf.operators.math.norm(field=disp_field, server=server)
    norm_field = norm_op.outputs.field()

    min_max_op = dpf.operators.min_max.min_max(field=norm_field, server=server)
    max_val = min_max_op.outputs.field_max().data[0]
    threshold = float(max_val * percent_threshold / 100.0)

    hp_op = dpf.operators.filter.field_high_pass(
        server=server, field=norm_field, threshold=threshold
    )
    above_scoping = hp_op.outputs.field().scoping

    rescope_op = dpf.operators.scoping.rescope(
        server=server, fields=disp_field, mesh_scoping=above_scoping
    )
    filtered_disp = rescope_op.outputs.fields_as_field()
    filtered_disp.meshed_region = model.metadata.meshed_region

    time_freq = tf.time_frequencies.data[set_id - 1]
    return [
        AnnotatedField(
            field=filtered_disp,
            name=f"displacement_above_threshold;{set_id}",
            display_name="Displacement Above Threshold",
            set_id=set_id,
            time_freq=time_freq,
            time_freq_unit=simulation.time_freq_support.time_frequencies.unit,
        )
    ]
"""


@pytest.fixture
def solution(rx: Client, rst_multiple_connections: str) -> Generator[Solution, None, None]:
    sol = rx.create_solution(
        name="Above Threshold Test Solution",
        result_provider_name="Local",
        file_path=rst_multiple_connections,
    )
    yield sol
    rx.delete_solution(sol)


def test_create_above_threshold_plot(solution: Solution):
    """A user-defined plot using the above-threshold script can be created."""
    plot_view = solution.create_plot(
        models.PlotDefinitionCreate(
            name="Displacement Above Threshold",
            result_type=models.ResultType.RESULT_TYPE_USER_DEFINED,
            location="unused",
            on_skin=False,
            all_sets=False,
            last_set=True,
            shell_position=models.ShellPosition.SHELL_POSITION_TOP,
            script=ABOVE_THRESHOLD_SCRIPT,
        )
    )

    plot_def = plot_view.definition

    assert plot_def.id is not None
    assert plot_def.name == "Displacement Above Threshold"
    assert plot_def.result_type == models.ResultType.RESULT_TYPE_USER_DEFINED
    assert plot_def.last_set is True
    assert plot_def.all_sets is False


def test_above_threshold_plot_in_viewport(rx: Client, solution: Solution):
    """The above-threshold plot renders without error when assigned to a viewport."""
    plot_view = solution.create_plot(
        models.PlotDefinitionCreate(
            name="Displacement Above Threshold",
            result_type=models.ResultType.RESULT_TYPE_USER_DEFINED,
            location="Nodal",
            on_skin=False,
            all_sets=False,
            last_set=True,
            script=ABOVE_THRESHOLD_SCRIPT,
        )
    )

    workspace = rx.create_workspace("Above Threshold Test Workspace")
    viewport = workspace.assign_view(view=plot_view, wait=True)

    assert viewport.id in workspace.viewport_ids
    assert viewport.view_id == plot_view.definition.id
    assert viewport.solution_id == solution.id


# Script that reads percent_threshold from the plot's custom_options, falling
# back to 50.0 if not set. This exercises the custom option plumbing.
ABOVE_THRESHOLD_CUSTOM_OPTION_SCRIPT = """\
from ansys.dpf import core as dpf
from ansys.result_explorer.server.simulation import SimulationInterface
from ansys.result_explorer.server.plots import PlotDefinition
from ansys.result_explorer.server.utils import AnnotatedField, UserDefinedContext


def get_custom_plot_data(
    simulation: SimulationInterface,
    definition: PlotDefinition,
    context: UserDefinedContext,
) -> list[AnnotatedField]:
    model = simulation.dpf_model
    server = simulation.server

    percent_threshold = float(definition.custom_options.get("percent_threshold", 50.0))

    tf = model.metadata.time_freq_support
    set_id = tf.n_sets

    disp_op = model.results.displacement()
    disp_op.inputs.time_scoping([set_id])
    fc_disp = disp_op.outputs.fields_container()
    disp_field = fc_disp[0]

    norm_op = dpf.operators.math.norm(field=disp_field, server=server)
    norm_field = norm_op.outputs.field()

    min_max_op = dpf.operators.min_max.min_max(field=norm_field, server=server)
    max_val = min_max_op.outputs.field_max().data[0]
    threshold = float(max_val * percent_threshold / 100.0)

    hp_op = dpf.operators.filter.field_high_pass(
        server=server, field=norm_field, threshold=threshold
    )
    above_scoping = hp_op.outputs.field().scoping

    rescope_op = dpf.operators.scoping.rescope(
        server=server, fields=disp_field, mesh_scoping=above_scoping
    )
    filtered_disp = rescope_op.outputs.fields_as_field()
    filtered_disp.meshed_region = model.metadata.meshed_region

    time_freq = tf.time_frequencies.data[set_id - 1]
    return [
        AnnotatedField(
            field=filtered_disp,
            name=f"displacement_above_threshold;{set_id}",
            display_name="Displacement Above Threshold",
            set_id=set_id,
            time_freq=time_freq,
            time_freq_unit=simulation.time_freq_support.time_frequencies.unit,
        )
    ]
"""


@pytest.mark.xfail(reason="custom_options passthrough to user-defined script not yet implemented")
def test_above_threshold_plot_custom_option_in_viewport(rx: Client, solution: Solution):
    """The percent_threshold custom option is passed through to the script and used."""
    plot_view = solution.create_plot(
        models.PlotDefinitionCreate(
            name="Displacement Above Threshold (custom option)",
            result_type=models.ResultType.RESULT_TYPE_USER_DEFINED,
            location="Nodal",
            on_skin=False,
            all_sets=False,
            last_set=True,
            script=ABOVE_THRESHOLD_CUSTOM_OPTION_SCRIPT,
            custom_options={"percent_threshold": 75.0},
        )
    )

    workspace = rx.create_workspace("Above Threshold Custom Option Workspace")
    viewport = workspace.assign_view(view=plot_view, wait=True)

    assert viewport.id in workspace.viewport_ids
    assert viewport.view_id == plot_view.definition.id
    assert viewport.solution_id == solution.id
