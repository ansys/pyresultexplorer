import logging

import pytest
from google.protobuf.json_format import MessageToDict

from ansys.result_explorer.core import models
from ansys.result_explorer.core.entities import Solution

log = logging.getLogger(__name__)


def test_plot(multiple_connections_solution: Solution):
    """CRUD operations for plot."""

    sol = multiple_connections_solution

    # create a new plot
    plot_def = models.PlotDefinitionCreate(
        name="My stress plot",
        result_type=models.ResultType.RESULT_TYPE_STRESS,
        location="Nodal",
        last_set=False,
        all_sets=True,
        on_skin=True,
        shell_position=models.ShellPosition.SHELL_POSITION_MIDDLE,
        fields=[
            models.Field(name="equivalent_von_mises_stress"),
            models.Field(name="stress_tensor", components=["XX", "ZZ"]),
        ],
    )

    plot_def = sol.create_plot(plot_def)

    assert plot_def.id is not None
    assert plot_def.name == "My stress plot"
    assert plot_def.result_type == models.ResultType.RESULT_TYPE_STRESS
    assert plot_def.on_skin is True
    assert plot_def.supports_monitoring is True
    assert plot_def.shell_position == models.ShellPosition.SHELL_POSITION_MIDDLE
    assert plot_def.all_sets is True
    assert plot_def.last_set is False

    # verify the plot is in the solution's plots
    plot_def_in_sol = next((p for p in sol.plots if p.id == plot_def.id), None)
    assert plot_def_in_sol is not None
    assert plot_def_in_sol.fields[0].name == "equivalent_von_mises_stress"
    assert plot_def_in_sol.fields[1].name == "stress_tensor"
    assert plot_def_in_sol.fields[1].components == ["XX", "ZZ"]

    # update the plot
    plot_def.name = "Updated stress plot"
    plot_def.all_sets = False
    plot_def.last_set = True
    plot_def = sol.update_plot(plot_def)

    assert plot_def.name == "Updated stress plot"

    plot_def_in_sol = next((p for p in sol.plots if p.id == plot_def.id), None)
    assert plot_def_in_sol is not None
    assert plot_def_in_sol.name == "Updated stress plot"
    assert plot_def_in_sol.all_sets is False
    assert plot_def_in_sol.last_set is True

    # delete the plot
    sol.delete_plot(plot_def.id)
    plot_def_in_sol = next((p for p in sol.plots if p.id == plot_def.id), None)
    assert plot_def_in_sol is None


def test_plot_with_default_result_type(multiple_connections_solution: Solution):
    """Make sure that a plot using the default result type (displacement)
    can be created without error.

    This is a regression test for a bug where the server would return an error
    if the result type was not explicitly set, which is the case when setting
    the result type to displacement since it's the default and protobuf does not
    serialize default values.
    """

    sol = multiple_connections_solution

    plot_def = models.PlotDefinitionCreate(
        name="test plot",
        result_type=models.ResultType.RESULT_TYPE_DISPLACEMENT,
        location="Nodal",
        last_set=True,
        all_sets=False,
        on_skin=True,
        shell_position=models.ShellPosition.SHELL_POSITION_MIDDLE,
        fields=[models.Field(name="displacement")],
    )

    serialized_plot_def = MessageToDict(plot_def, preserving_proto_field_name=True)
    assert "result_type" not in serialized_plot_def

    plot_def = sol.create_plot(plot_def)

    assert plot_def.id is not None
    assert plot_def.result_type == models.ResultType.RESULT_TYPE_DISPLACEMENT


@pytest.mark.xfail(reason="Needs to be fixed in the web app.")
def test_new_plot_added_to_views(multiple_connections_solution: Solution):
    """Ensure that a new plot is added to the solution's views."""

    sol = multiple_connections_solution

    plot_def = models.PlotDefinitionCreate(
        name="New plot",
        result_type=models.ResultType.RESULT_TYPE_DISPLACEMENT,
        location="Nodal",
        last_set=True,
        all_sets=False,
        on_skin=True,
        shell_position=models.ShellPosition.SHELL_POSITION_MIDDLE,
        fields=[models.Field(name="displacement")],
    )

    existing_view_ids = {v.id for v in sol.views}
    plot_def = sol.create_plot(plot_def)
    log.warning(sol.views)

    new_plot_views = [
        v
        for v in sol.views
        if v.id not in existing_view_ids and v.type == models.ViewType.VIEW_TYPE_PLOT
    ]
    view = next((v for v in new_plot_views if v.name == plot_def.name), None)
    assert view is not None
