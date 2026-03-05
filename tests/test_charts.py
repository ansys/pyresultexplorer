import logging

from ansys.result_explorer.core import models
from ansys.result_explorer.core.entities import Solution

log = logging.getLogger(__name__)


def test_chart(multiple_connections_solution: Solution):
    """CRUD operations for chart."""

    sol = multiple_connections_solution

    # create a new chart
    chart_def = models.ChartDefinitionCreate(
        name="My chart",
        user_defined=False,
        all_sets=True,
        results=[
            models.ChartResult(
                name="Stress",
                result_type=models.ResultType.RESULT_TYPE_STRESS,
                location="Nodal",
                fields=[
                    models.Field(name="equivalent_von_mises_stress"),
                    models.Field(name="stress_tensor", components=["XX", "ZZ"]),
                ],
                filters=[models.Filter.FILTER_MAX],
            )
        ],
    )

    chart_def = sol.create_chart(chart_def)

    assert chart_def.id is not None
    assert chart_def.name == "My chart"
    assert chart_def.user_defined is False
    assert chart_def.all_sets is True
    assert len(chart_def.results) == 1
    assert chart_def.results[0].filters[0] == models.Filter.FILTER_MAX

    # verify the chart is in the solution's charts
    chart_def_in_sol = next((c for c in sol.charts if c.id == chart_def.id), None)
    assert chart_def_in_sol is not None
    assert chart_def_in_sol.results[0].name == "Stress"
    assert chart_def_in_sol.results[0].fields[0].name == "equivalent_von_mises_stress"
    assert chart_def_in_sol.results[0].fields[1].name == "stress_tensor"
    assert chart_def_in_sol.results[0].fields[1].components == ["XX", "ZZ"]

    # update the chart
    chart_def.name = "Updated chart"
    chart_def.results[0].name = "Updated Stress"
    chart_def = sol.update_chart(chart_def)

    assert chart_def.name == "Updated chart"

    chart_def_in_sol = next((c for c in sol.charts if c.id == chart_def.id), None)
    assert chart_def_in_sol is not None
    assert chart_def_in_sol.name == "Updated chart"
    assert chart_def_in_sol.results[0].name == "Updated Stress"

    # delete the chart
    sol.delete_chart(chart_def.id)
    chart_def_in_sol = next((c for c in sol.charts if c.id == chart_def.id), None)
    assert chart_def_in_sol is None
