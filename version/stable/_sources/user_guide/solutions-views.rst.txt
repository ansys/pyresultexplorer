Solutions and views
###################

When a solution is created, Result Explorer automatically creates predefined views.
The available predefined views depend on the solution type and on the result data available in the solution files.

Creating a solution
===================

You create a :class:`Solution <ansys.result_explorer.core.Solution>` object using the client:

.. code:: python

    from ansys.result_explorer.core import launch_result_explorer

    rx = launch_result_explorer()

    # Create a solution from a result file
    solution = rx.create_solution(
        name="My Solution",
        file_path="/path/to/result/file.rst"
    )

    print(solution)


The solution object provides access to rich metadata about the loaded results, including but not limited to:

-  General info: name, description, ID
-  Analysis info: physics type, analysis type, solver version, unit system
-  Mesh info: number of nodes/elements, distance unit
-  Time/frequency info: number of result sets, time/frequency values and unit
-  Mesh entities info: named selections and bodies
-  Available results for plots and charts


Named selections
================

A solution can include named selections (groups of elements/nodes), which can be either solver-defined or custom-defined in Result Explorer.

.. code:: python

    # List solver-defined named selections
    for ns in solution.solver_named_selections:
        print(f"- {ns}")

    # List named selections created in Result Explorer
    for ns in solution.named_selections:
        print(f"- {ns.name}: {ns.description}")


You can also create new named selections programmatically using the :meth:`Solution.create_named_selection() <ansys.result_explorer.core.Solution.create_named_selection>` method.

.. code:: python

    from ansys.result_explorer.core import models

    # Create a named selection from a range of element IDs
    ns_range = solution.create_named_selection(
        models.NamedSelectionCreate(
            name="Elements 23-28",
            type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
            element_ids=[models.IdsScoping(range=models.Range(min=23, max=28))],
        )
    )

    # Create a named selection from specific element IDs
    ns_list = solution.create_named_selection(
        models.NamedSelectionCreate(
            name="Selected Elements",
            type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
            element_ids=[models.IdsScoping(values=[3, 4, 7, 8, 9, 11, 13])],
        )
    )

Views
=====

A view represents a specific analysis result that can be displayed in a viewport. Predefined views are created automatically when
a solution is loaded based on the available result data, but you can also create your own.

Creating a view doesn't trigger any computation or result evaluation. It simply defines what data to display.
The actual data retrieval happens when the view is displayed in a viewport.

Once a view is shown in at least one viewport, subsequent changes to the view definition trigger its re-evaluation.

Accessing predefined views
--------------------------

Predefined views are automatically created based on the solution's result data:

.. code:: python

    # List all available views in the solution
    views = solution.views
    for view in views:
        print(f"- {view.name} (type: {view.type})")

    # Find a specific view by name
    displacement_view = next(
        (v for v in views if "Displacement" in v.name),
        None
    )

View types
----------

PyResultExplorer supports the following types of views:

- **Mesh views**: Display the mesh of the model
- **Plot views**: Display results as 3D contours on the mesh
- **Chart views**: Display results as charts (for example, line plots, bar charts)
- **Convergence trackers**: Display solver convergence across iterations
- **Contact trackers**: Visualize and analyze contact behavior

Creating a new view
-------------------

You can programmatically create new plot and chart views using the :meth:`Solution.create_plot() <ansys.result_explorer.core.Solution.create_plot>`
and :meth:`Solution.create_chart() <ansys.result_explorer.core.Solution.create_chart>` methods.

The following example creates a displacement plot on a named selection at a specific time step:

.. code:: python

    from ansys.result_explorer.core import (
        Component,
        Field,
        Location,
        PlotDefinition,
        ResultFieldName,
        ResultType,
    )
    from ansys.result_explorer.core import models

    # Create a named selection first (optional, but useful for filtering)
    ns = solution.create_named_selection(
        models.NamedSelectionCreate(
            name="Region of Interest",
            type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
            element_ids=[models.IdsScoping(range=models.Range(min=23, max=28))],
        )
    )

    # Create a plot view showing Y-displacement on the named selection
    plot_view = solution.create_plot(
        PlotDefinition(
            name="Displacement Y - Region of Interest",
            result_type=ResultType.displacement,
            location=Location.nodal,
            fields=[Field(ResultFieldName.displacement, components=[Component.Y])],
            named_selection_id=ns.id,
            set_ids=[5],  # Show results at time step 5
            all_sets=False,
            last_set=False,
        )
    )

    # Display the plot in a viewport
    viewport = workspace.assign_view(view=plot_view, wait=True)

Similarly, you can create a chart view. The following example creates a chart showing
the maximum normal stress in the X direction over all time steps:

.. code:: python

    from ansys.result_explorer.core import (
        ChartDefinition,
        ChartResult,
        Component,
        Field,
        Filter,
        Location,
        ResultFieldName,
        ResultType,
    )

    # Create a chart showing max normal stress in X direction over time
    chart_view = solution.create_chart(
        ChartDefinition(
            name="Max Stress XX Over Time",
            all_sets=True,
            results=[
                ChartResult(
                    name="Max Stress XX",
                    result_type=ResultType.stress,
                    location=Location.nodal,
                    fields=[Field(ResultFieldName.stress_tensor, components=[Component.XX])],
                    filters=[Filter.max],
                )
            ],
        )
    )
