"""Solution entity class."""

from __future__ import annotations

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

    @property
    def description(self) -> str:
        """Solution description."""
        return self._pb.description

    @property
    def cache_plot_data(self) -> bool:
        """Whether to cache plot data."""
        return self._pb.cache_plot_data

    @property
    def files(self) -> list:
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
    def available_named_selections(self) -> list:
        """Available named selections."""
        return list(self._pb.available_named_selections)

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
    def element_groups(self) -> list:
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
