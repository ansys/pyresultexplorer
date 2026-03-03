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


class Solution(NamedBaseEntity[models.Solution]):
    """Represents a solution loaded in the server."""

    def _get(self):
        """Get the latest solution data from the server."""
        self._pb = self._client._solution_stub.Get(
            models.ResourceId(id=self.id),
            metadata=self._client._grpc_metadata,
        )

    def create_plot(self, definition: models.PlotDefinitionCreate) -> models.PlotDefinition:
        """Create a plot based on a plot definition."""
        pb_plot = self._client._solution_stub.CreatePlotDefinition(
            models.CreatePlotDefinitionRequest(solution_id=self.id, plot_definition=definition),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return pb_plot

    def update_plot(
        self, definition: models.PlotDefinitionCreate | models.PlotDefinition
    ) -> models.PlotDefinition:
        """Update a plot based on a plot definition."""

        plot_def = definition
        if isinstance(definition, models.PlotDefinition):
            plot_def = _clone_msg_to_compatible_type(definition, models.PlotDefinitionCreate)

        pb_plot = self._client._solution_stub.UpdatePlotDefinition(
            models.UpdatePlotDefinitionRequest(
                solution_id=self.id, plot_definition_id=definition.id, plot_definition=plot_def
            ),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return pb_plot

    def delete_plot(self, id: str) -> None:
        """Delete a plot by ID."""
        self._client._solution_stub.DeletePlotDefinition(
            models.DeletePlotDefinitionRequest(solution_id=self.id, plot_definition_id=id),
            metadata=self._client._grpc_metadata,
        )
        self._get()

    def create_chart(self, definition: models.ChartDefinitionCreate) -> models.ChartDefinition:
        """Create a chart based on a chart definition."""
        pb_chart = self._client._solution_stub.CreateChartDefinition(
            models.CreateChartDefinitionRequest(solution_id=self.id, chart_definition=definition),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return pb_chart

    def update_chart(
        self, definition: models.ChartDefinitionCreate | models.ChartDefinition
    ) -> models.ChartDefinition:
        """Update a chart based on a chart definition."""

        chart_def = definition
        if isinstance(definition, models.ChartDefinition):
            chart_def = _clone_msg_to_compatible_type(definition, models.ChartDefinitionCreate)

        pb_chart = self._client._solution_stub.UpdateChartDefinition(
            models.UpdateChartDefinitionRequest(
                solution_id=self.id, chart_definition_id=definition.id, chart_definition=chart_def
            ),
            metadata=self._client._grpc_metadata,
        )
        self._get()
        return pb_chart

    def delete_chart(self, id: str) -> None:
        """Delete a chart by ID."""
        self._client._solution_stub.DeleteChartDefinition(
            models.DeleteChartDefinitionRequest(solution_id=self.id, chart_definition_id=id),
            metadata=self._client._grpc_metadata,
        )
        self._get()

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
        """Available result types."""
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
    def mesh_scopings(self) -> list:
        """Mesh scoping definitions."""
        return list(self._pb.mesh_scopings)

    @property
    def configurable_plots(self) -> list[models.ConfigurablePlot]:
        """Configurable plot definitions."""
        return list(self._pb.configurable_plots)

    @property
    def plots(self) -> list[models.PlotDefinition]:
        """Plot definitions."""
        return list(self._pb.plots)

    @property
    def configurable_charts(self) -> list[models.ConfigurableChart]:
        """Configurable chart definitions."""
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

    @property
    def views(self) -> list[View]:
        """List of views available in this solution."""
        return [View(v, self._client, parent=self) for v in self._pb.views]

    def __str__(self) -> str:
        """Return a formatted string representation of the solution."""
        lines = [
            "=" * 70,
            f"Solution: {self.name}",
            "=" * 70,
            f"{'ID:':<20}{self.id}",
            f"{'Description:':<20}{self.description or 'N/A'}",
            "",
            "Analysis Information:",
            f"  {'Physics Type:':<20}{self.physics_type or 'N/A'}",
            f"  {'Analysis Type:':<20}{self.analysis_type or 'N/A'}",
            f"  {'Solver Version:':<20}{self.solver_version or 'N/A'}",
            f"  {'Unit System:':<20}{self.unit_system or 'N/A'}",
            "",
            "Mesh Information:",
            f"  {'Num Elements:':<20}{self.n_elements}",
            f"  {'Num Nodes:':<20}{self.n_nodes}",
            f"  {'Num Named Selections:':<20}{len(self.named_selections)}",
            f"  {'Num Bodies:':<20}{len(self.bodies)}",
            f"  {'Distance Unit:':<20}{self.distance_unit or 'N/A'}",
            "",
            "Results Information:",
            f"  {'Num Sets:':<20}{self.n_sets}",
            f"  {'Available Results:':<20}{self.n_results}",
            f"  {'Time/Freq Unit:':<20}{self.time_frequencies_unit or 'N/A'}",
            "",
            "Status:",
            f"  {'Ready:':<20}{'Yes' if self.ready else 'No'}",
            f"  {'Live:':<20}{'Yes' if self.live else 'No'}",
        ]

        if self.errors:
            lines.extend(
                [
                    "",
                    "Errors:",
                ]
            )
            for error in self.errors:
                lines.append(f"  - {error}")

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
