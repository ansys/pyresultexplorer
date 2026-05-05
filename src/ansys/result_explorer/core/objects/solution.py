"""Solution entity class."""

from __future__ import annotations

from google.protobuf.json_format import MessageToDict, ParseDict

from .. import models
from .base import NamedBaseEntity, SubEntity

# from .solution_dataclasses import AvailableMeshProperty, AvailableResult, TimeFrequency


class View(SubEntity[models.View, "Solution"]):
    """Represents a result view in a solution."""

    @property
    def type(self) -> models.ViewType:
        """View type."""
        return self._pb.type

    @property
    def solution(self) -> Solution:
        """Parent solution of this view."""
        return self.parent


class PlotView(View):
    """Represents a plot view in a solution."""

    @property
    def definition(self) -> models.PlotDefinition:
        """Plot definition associated with this view."""
        plot_def_id = self._pb.id
        plot_def = next((p for p in self.solution.plots if p.id == plot_def_id), None)
        if plot_def is None:
            raise RuntimeError(
                f"Plot definition with ID {plot_def_id} not found in solution {self.solution.name}"
            )
        return plot_def


class ChartView(View):
    """Represents a chart view in a solution."""

    @property
    def definition(self) -> models.ChartDefinition:
        """Chart definition associated with this view."""
        chart_def_id = self._pb.id
        chart_def = next((c for c in self.solution.charts if c.id == chart_def_id), None)
        if chart_def is None:
            raise RuntimeError(
                f"Chart definition with ID {chart_def_id} "
                f"not found in solution {self.solution.name}"
            )
        return chart_def


class MeshView(View):
    """Represents a mesh view in a solution."""

    @property
    def options(self) -> models.MeshGraphicsOptions:
        """Mesh view options."""
        return self.solution.mesh_options


class Solution(NamedBaseEntity[models.Solution]):
    """Represents a solution loaded in the server."""

    def __init__(self, pb_obj: models.Solution, client):
        super().__init__(pb_obj, client)

        self._result_provider: models.ResultProvider | None = None

    def _get(self):
        """Get the latest solution data from the server."""
        self._pb = self._client._solution_stub.Get(
            models.ResourceId(id=self.id),
            metadata=self._client._grpc_metadata,
        )

    def _get_plot_view(self, plot_def_id: str) -> PlotView:
        """Get the PlotView associated with a given plot definition ID."""
        for view in self.views:
            if view.type == models.ViewType.VIEW_TYPE_PLOT and view.id == plot_def_id:
                return PlotView(view._pb, self._client, parent=self)
        raise RuntimeError(
            f"No PlotView found for plot definition ID {plot_def_id} in solution {self.name}"
        )

    def _get_chart_view(self, chart_def_id: str) -> ChartView:
        """Get the ChartView associated with a given chart definition ID."""
        for view in self.views:
            if view.type == models.ViewType.VIEW_TYPE_CHART and view.id == chart_def_id:
                return ChartView(view._pb, self._client, parent=self)
        raise RuntimeError(
            f"No ChartView found for chart definition ID {chart_def_id} in solution {self.name}"
        )

    def create_plot(self, definition: models.PlotDefinitionCreate) -> PlotView:
        """Create a plot based on a plot definition."""
        pb_plot = self._client._solution_stub.CreatePlotDefinition(
            models.CreatePlotDefinitionRequest(solution_id=self.id, plot_definition=definition),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return self._get_plot_view(pb_plot.id)

    def update_plot(
        self, plot: models.PlotDefinitionCreate | models.PlotDefinition | PlotView
    ) -> PlotView:
        """Update a plot based on a plot definition."""

        plot_def = plot
        if isinstance(plot, models.PlotDefinition):
            plot_def = _clone_msg_to_compatible_type(plot, models.PlotDefinitionCreate)
        elif isinstance(plot, PlotView):
            plot_def = plot.definition

        pb_plot = self._client._solution_stub.UpdatePlotDefinition(
            models.UpdatePlotDefinitionRequest(
                solution_id=self.id, plot_definition_id=plot_def.id, plot_definition=plot_def
            ),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return self._get_plot_view(pb_plot.id)

    def delete_plot(self, id: str | PlotView | models.PlotDefinition) -> None:
        """Delete a plot by ID."""
        plot_id = id
        if isinstance(id, PlotView):
            plot_id = id.definition.id
        elif isinstance(id, models.PlotDefinition):
            plot_id = id.id

        self._client._solution_stub.DeletePlotDefinition(
            models.DeletePlotDefinitionRequest(solution_id=self.id, plot_definition_id=plot_id),
            metadata=self._client._grpc_metadata,
        )
        self._get()

    def create_chart(self, definition: models.ChartDefinitionCreate) -> ChartView:
        """Create a chart based on a chart definition."""
        pb_chart = self._client._solution_stub.CreateChartDefinition(
            models.CreateChartDefinitionRequest(solution_id=self.id, chart_definition=definition),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return self._get_chart_view(pb_chart.id)

    def update_chart(
        self, chart: models.ChartDefinitionCreate | models.ChartDefinition | ChartView
    ) -> ChartView:
        """Update a chart based on a chart definition."""

        chart_def = chart
        if isinstance(chart, models.ChartDefinition):
            chart_def = _clone_msg_to_compatible_type(chart, models.ChartDefinitionCreate)
        elif isinstance(chart, ChartView):
            chart_def = chart.definition

        pb_chart = self._client._solution_stub.UpdateChartDefinition(
            models.UpdateChartDefinitionRequest(
                solution_id=self.id, chart_definition_id=chart_def.id, chart_definition=chart_def
            ),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return self._get_chart_view(pb_chart.id)

    def delete_chart(self, id: str | ChartView | models.ChartDefinition) -> None:
        """Delete a chart by ID."""
        chart_id = id
        if isinstance(id, ChartView):
            chart_id = id.definition.id
        elif isinstance(id, models.ChartDefinition):
            chart_id = id.id

        self._client._solution_stub.DeleteChartDefinition(
            models.DeleteChartDefinitionRequest(solution_id=self.id, chart_definition_id=chart_id),
            metadata=self._client._grpc_metadata,
        )
        self._get()

    def create_named_selection(
        self, definition: models.NamedSelectionCreate
    ) -> models.NamedSelection:
        """Create a named selection."""
        pb_ns = self._client._solution_stub.CreateNamedSelection(
            models.CreateNamedSelectionRequest(solution_id=self.id, named_selection=definition),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return pb_ns

    def delete_named_selection(self, id: str) -> None:
        """Delete a named selection by ID."""
        self._client._solution_stub.DeleteNamedSelection(
            models.DeleteNamedSelectionRequest(solution_id=self.id, named_selection_id=id),
            metadata=self._client._grpc_metadata,
        )
        self._get()

    def update_named_selection(
        self, definition: models.NamedSelectionCreate | models.NamedSelection
    ) -> models.NamedSelection:
        """Update a named selection."""

        ns_def = definition
        if isinstance(definition, models.NamedSelection):
            ns_def = _clone_msg_to_compatible_type(definition, models.NamedSelectionCreate)

        pb_ns = self._client._solution_stub.UpdateNamedSelection(
            models.UpdateNamedSelectionRequest(
                solution_id=self.id, named_selection_id=definition.id, named_selection=ns_def
            ),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return pb_ns

    @property
    def result_provider(self) -> models.ResultProvider:
        """Result provider for this solution."""
        if self._result_provider is None:
            sol_id = self.id
            rps = self._client.list_result_providers()
            rp = next((rp for rp in rps if sol_id in rp.solution_ids), None)
            if rp is None:
                raise RuntimeError(f"Result provider with solution ID {sol_id} not found")

            self._result_provider = rp
        return self._result_provider

    @property
    def id(self) -> str:
        """Unique identifier."""
        return self._pb.id

    @property
    def name(self) -> str:
        """Solution name."""
        return self._pb.name

    @property
    def description(self) -> str:
        """Solution description."""
        return self._pb.description

    @property
    def cache_plot_data(self) -> bool:
        """Whether to cache plot data."""
        return self._pb.cache_plot_data

    @property
    def files(self) -> list[models.File]:
        """List of result files."""
        return list(self._pb.files)

    @property
    def creation_time(self) -> str:
        """Timestamp of solution creation."""
        return self._pb.creation_time

    @property
    def ready(self) -> bool:
        """Whether solution is ready."""
        return self._pb.ready

    @property
    def errors(self) -> list[str]:
        """List of error messages."""
        return list(self._pb.errors)

    @property
    def live(self) -> bool:
        """Whether the simulation is currently running."""
        return self._pb.live

    @property
    def outdated(self) -> bool:
        """Whether solution data is outdated wrt to the result files."""
        return self._pb.outdated

    @property
    def solver_named_selections(self) -> list[str]:
        """Solver named selections."""
        return list(self._pb.solver_named_selections)

    @property
    def mesh_options(self) -> models.MeshGraphicsOptions:
        """Mesh graphics options."""
        return self._pb.mesh_graphics_options

    @property
    def named_selections(self) -> list[models.NamedSelection]:
        """Named selections."""
        return list(self._pb.named_selections)

    @property
    def available_custom_selections(self) -> list:
        """Available custom selections."""
        return list(self._pb.available_custom_selections)

    @property
    def n_elements(self) -> int:
        """Number of elements in the solution mesh."""
        return self._pb.n_elements

    @property
    def n_nodes(self) -> int:
        """Number of nodes in the solution mesh."""
        return self._pb.n_nodes

    @property
    def distance_unit(self) -> str:
        """Unit for distance measurements."""
        return self._pb.distance_unit

    @property
    def element_groups(self) -> list[models.ElementGroup]:
        """Element groups in the mesh."""
        return list(self._pb.element_groups)

    @property
    def unsupported_element_types(self) -> list[str]:
        """Unsupported element types."""
        return list(self._pb.unsupported_element_types)

    @property
    def physics_type(self) -> str:
        """Type of physics analysis."""
        return self._pb.physics_type

    @property
    def analysis_type(self) -> str:
        """Type of analysis performed."""
        return self._pb.analysis_type

    @property
    def unit_system(self) -> str:
        """Unit system used."""
        return self._pb.unit_system

    @property
    def n_results(self) -> int:
        """Number of results available."""
        return self._pb.n_results

    @property
    def solver_version(self) -> str:
        """Version of solver used."""
        return self._pb.solver_version

    @property
    def available_results(self) -> list[models.AvailableResult]:
        """Available DPF result types.

        List of all available DPF results in the solution,
        including those that may not be supported in Result Explorer yet.
        """
        return list(self._pb.available_results)

    @property
    def available_trackers(self) -> list:
        """Available tracker types."""
        return list(self._pb.available_trackers)

    @property
    def available_mesh_properties(self) -> list[models.AvailableMeshProperty]:
        """Available mesh properties."""
        return list(self._pb.available_mesh_properties)

    @property
    def n_sets(self) -> int:
        """Number of result sets."""
        return self._pb.n_sets

    @property
    def time_frequencies(self) -> list[models.TimeFrequency]:
        """Time/frequency data."""
        return list(self._pb.time_frequencies)

    @property
    def time_frequencies_unit(self) -> str:
        """Unit for time/frequencies."""
        return self._pb.time_frequencies_unit

    @property
    def configurable_plots(self) -> list[models.ConfigurablePlot]:
        """Configurable plot definitions.

        Provides a list of results with supported and configurable options
        that can be used to create plots.
        """
        return list(self._pb.configurable_plots)

    @property
    def plots(self) -> list[models.PlotDefinition]:
        """Plot definitions."""
        return list(self._pb.plots)

    @property
    def configurable_charts(self) -> list[models.ConfigurableChart]:
        """Configurable chart definitions.

        Provides a list of results with supported and configurable options
        that can be used to create charts.
        """
        return list(self._pb.configurable_charts)

    @property
    def charts(self) -> list[models.ChartDefinition]:
        """Chart definitions."""
        return list(self._pb.charts)

    @property
    def bodies(self) -> list[models.Body]:
        """Bodies in the model."""
        return list(self._pb.bodies)

    @property
    def solver_text_outputs(self) -> list[models.SolverTextOutputFile]:
        """Solver text output files."""
        return list(self._pb.solver_text_outputs)

    def get_solver_out_content(
        self, file: str | models.SolverTextOutputFile, lines_offset: int = 0
    ) -> str:
        """Get content of a solver text output file."""
        if isinstance(file, models.SolverTextOutputFile):
            solver_out = file
        else:
            solver_out = next((f for f in self.solver_text_outputs if f.name == file), None)
        if solver_out is None:
            raise ValueError(
                f"Solver text output file '{file}' not found in solution '{self.name}'"
            )
        content = self._client._get_file_content(
            path=solver_out.path,
            result_provider=self.result_provider.name,
            lines_offset=lines_offset,
        )
        return content

    @property
    def views(self) -> list[View]:
        """List of views available in this solution."""
        views = []
        for v in self._pb.views:
            if v.type == models.ViewType.VIEW_TYPE_PLOT:
                views.append(PlotView(v, self._client, parent=self))
            elif v.type == models.ViewType.VIEW_TYPE_CHART:
                views.append(ChartView(v, self._client, parent=self))
            elif v.type == models.ViewType.VIEW_TYPE_MESH:
                views.append(MeshView(v, self._client, parent=self))
            else:
                views.append(View(v, self._client, parent=self))
        return views

    def __str__(self) -> str:
        """Return a formatted string representation of the solution."""

        lines = [
            "\n",
            "=" * 70,
            f"Solution: {self.name}",
            "=" * 70,
            f"{'ID:':<25}{self.id}",
            f"{'Description:':<25}{self.description or 'N/A'}",
            "",
            "Status:",
            f"  {'Ready:':<25}{'Yes' if self.ready else 'No'}",
            f"  {'Live:':<25}{'Yes' if self.live else 'No'}",
        ]

        if self.files:
            lines.extend(
                [
                    "",
                    "Result Files:",
                ]
            )
            for file in self.files[:5]:  # Show first 5 files
                lines.append(f"  - {file.path} (key: {file.key})")
            if len(self.files) > 5:
                lines.append(f"  ... and {len(self.files) - 5} more")

        lines.extend(
            [
                "",
                "Analysis Information:",
                f"  {'Physics Type:':<25}{self.physics_type or 'N/A'}",
                f"  {'Analysis Type:':<25}{self.analysis_type or 'N/A'}",
                f"  {'Solver Version:':<25}{self.solver_version or 'N/A'}",
                f"  {'Unit System:':<25}{self.unit_system or 'N/A'}",
                "",
                "Mesh Information:",
                f"  {'Num Elements:':<25}{self.n_elements}",
                f"  {'Num Nodes:':<25}{self.n_nodes}",
                f"  {'Num Named Selections:':<25}{len(self.named_selections)}",
                f"  {'Num Bodies:':<25}{len(self.bodies)}",
                f"  {'Distance Unit:':<25}{self.distance_unit or 'N/A'}",
                "",
                "Results Information:",
                f"  {'Num Sets:':<25}{self.n_sets}",
                f"  {'Available Results:':<25}{self.n_results}",
                f"  {'Time/Freq Unit:':<25}{self.time_frequencies_unit or 'N/A'}",
                "",
                "Available Plot Results:",
            ]
        )

        # Add configurable plots summary
        if self.configurable_plots:
            for plot in self.configurable_plots:
                # Convert RESULT_TYPE_DISPLACEMENT to Displacement
                result_type_name = models.ResultType.Name(plot.result_type).replace(
                    "RESULT_TYPE_", ""
                )
                result_type = " ".join(word.capitalize() for word in result_type_name.split("_"))
                lines.append(f"  {result_type}")
                for field in plot.fields:
                    components_str = f" [{', '.join(field.components)}]" if field.components else ""
                    lines.append(f"    - {field.name}{components_str}")
        else:
            lines.append("  No configurable plots available")

        if self.errors:
            lines.extend(
                [
                    "",
                    "Errors:",
                ]
            )
            for error in self.errors:
                lines.append(f"  - {error}")

        lines.append("=" * 70)
        return "\n".join(lines)


def _clone_msg_to_compatible_type(msg, target_msg_type: type):
    data = MessageToDict(
        msg,
        preserving_proto_field_name=True,
        use_integers_for_enums=True,
        always_print_fields_with_no_presence=True,
    )
    return ParseDict(
        data,
        target_msg_type(),
        ignore_unknown_fields=True,
    )
