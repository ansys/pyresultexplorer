import logging

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
