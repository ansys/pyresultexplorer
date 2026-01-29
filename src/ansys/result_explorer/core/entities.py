"""Pythonic wrapper objects for gRPC models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .client import Client

from . import models

PBType = TypeVar("PBType")


class BaseEntity(Generic[PBType]):
    """Base class for all domain objects wrapping protobuf messages."""

    def __init__(self, pb_obj: PBType, client: Client):
        self._pb: PBType = pb_obj
        self._client = client

    @property
    def id(self) -> str:
        """Unique identifier."""
        return self._pb.id

    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._pb.name if hasattr(self._pb, "name") else ""


class View(BaseEntity[models.View]):
    """Represents a result view in a solution."""

    @property
    def view_type(self):
        """View type (e.g., stress, displacement)."""
        return self._pb.view_type


class ViewMetadata:
    """Pythonic wrapper for viewport metadata."""

    def __init__(self, metadata_dict: dict, client: Client, viewport_id: str):
        self._metadata = dict(metadata_dict) if metadata_dict else {}
        self._client = client
        self._viewport_id = viewport_id

    @property
    def show_mesh_edges(self) -> bool:
        return self._metadata.get("show_mesh_edges", False)

    @show_mesh_edges.setter
    def show_mesh_edges(self, value: bool):
        self._metadata["show_mesh_edges"] = value

    @property
    def show_min_max_labels(self) -> bool:
        return self._metadata.get("show_min_max_labels", False)

    @show_min_max_labels.setter
    def show_min_max_labels(self, value: bool):
        self._metadata["show_min_max_labels"] = value

    def _to_dict(self) -> dict:
        """Convert back to dictionary for gRPC calls."""
        return self._metadata


class Viewport(BaseEntity[models.Viewport]):
    """Represents a viewport in a workspace."""

    @property
    def metadata(self) -> ViewMetadata:
        """Access viewport metadata as a pythonic object."""
        metadata_dict = dict(self._pb.metadata) if self._pb.metadata else {}
        return ViewMetadata(metadata_dict, self._client, self.id)

    def assign_view(self, solution: Solution, view: View, wait: bool = True) -> Viewport:
        """Assign a view to this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            solution_id=solution.id,
            view_id=view.id,
            wait=wait,
        )
        updated_pb = self._client._workspace_stub.UpdateViewport(
            req, metadata=self._client._grpc_metadata
        )
        self._pb = updated_pb
        return self

    def take_snapshot(self) -> bytes:
        """Take a snapshot of this viewport."""
        req = models.CreateSnapshotRequest(viewport_id=self.id)
        snapshot = self._client._workspace_stub.CreateSnapshot(
            req, metadata=self._client._grpc_metadata
        )
        return snapshot.data

    def modify_view_metadata(self, metadata: ViewMetadata) -> None:
        """Update metadata for this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            metadata=metadata._to_dict(),
            wait=True,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(
            req, metadata=self._client._grpc_metadata
        )


class Solution(BaseEntity[models.Solution]):
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
        """Whether solution is live/updating."""
        return self._pb.live

    @property
    def outdated(self) -> bool:
        """Whether solution data is outdated."""
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
    def available_results(self) -> list:
        """Available result types."""
        return list(self._pb.available_results)

    @property
    def available_trackers(self) -> list:
        """Available tracker types."""
        return list(self._pb.available_trackers)

    @property
    def available_mesh_properties(self) -> list:
        """Available mesh properties."""
        return list(self._pb.available_mesh_properties)

    @property
    def n_sets(self) -> int:
        """Number of result sets."""
        return self._pb.n_sets

    @property
    def time_frequencies(self) -> list:
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
    def configurable_plots(self) -> list:
        """Configurable plot definitions."""
        return list(self._pb.configurable_plots)

    @property
    def plots(self) -> list:
        """Plot definitions."""
        return list(self._pb.plots)

    @property
    def configurable_charts(self) -> list:
        """Configurable chart definitions."""
        return list(self._pb.configurable_charts)

    @property
    def charts(self) -> list:
        """Chart definitions."""
        return list(self._pb.charts)

    @property
    def bodies(self) -> list:
        """Bodies in the model."""
        return list(self._pb.bodies)

    @property
    def solver_text_outputs(self) -> list:
        """Solver text output files."""
        return list(self._pb.solver_text_outputs)

    @property
    def views(self) -> list[View]:
        """List of views available in this solution."""
        return [View(v, self._client) for v in self._pb.views]


class Workspace(BaseEntity[models.Workspace]):
    """Represents a workspace with viewports and solutions."""

    @property
    def sync_options(self):
        """Synchronization options for this workspace."""
        return self._pb.sync_options

    @property
    def viewport_ids(self) -> list[str]:
        """List of viewport IDs in this workspace."""
        return list(self._pb.viewport_ids)

    @property
    def fullscreen_viewport_id(self) -> str:
        """ID of the viewport in fullscreen mode, or empty string if none."""
        return self._pb.fullscreen_viewport_id

    @property
    def viewports(self) -> list[Viewport]:
        """List viewports in this workspace."""
        vp_response = self._client._workspace_stub.ListViewports(
            models.ResourceId(id=self.id), metadata=self._client._grpc_metadata
        )
        return [Viewport(v, self._client) for v in vp_response.viewports]

    def create_viewport(self, viewport: Viewport, direction) -> Viewport:
        """Create a new viewport as a child of the given viewport."""
        req = models.CreateViewportRequest(
            workspace_id=self.id,
            viewport_id=viewport.id,
            direction=direction,
        )
        pb_vp = self._client._workspace_stub.CreateViewport(
            req, metadata=self._client._grpc_metadata
        )
        return Viewport(pb_vp, self._client)

    def assign_view(self, solution: Solution, view: View, wait: bool = True) -> Viewport:
        """Assign a view to the first viewport in this workspace."""
        first_viewport = self.viewports[0]
        return first_viewport.assign_view(solution, view, wait=wait)

    def set_sync(
        self,
        camera: bool | None = None,
        time_freq: bool | None = None,
        legend: bool | None = None,
    ) -> None:
        """Update synchronization options for this workspace."""
        # Only update fields that are specified (partial update)
        sync_opts = models.SyncOptions()
        if camera is not None:
            sync_opts.camera = camera
        else:
            sync_opts.CopyFrom(self._pb.sync_options)
        if time_freq is not None:
            sync_opts.time_freq = time_freq
        if legend is not None:
            sync_opts.legend = legend

        req = models.WorkspaceUpdateRequest(
            workspace_id=self.id,
            sync_options=sync_opts,
        )
        self._pb = self._client._workspace_stub.Update(req, metadata=self._client._grpc_metadata)

    def set_fullscreen_viewport(self, viewport: Viewport) -> None:
        """Set a viewport to fullscreen mode."""
        req = models.WorkspaceUpdateRequest(
            workspace_id=self.id,
            fullscreen_viewport_id=viewport.id,
        )
        self._pb = self._client._workspace_stub.Update(req, metadata=self._client._grpc_metadata)

    def exit_fullscreen(self) -> None:
        """Exit fullscreen mode."""
        req = models.WorkspaceUpdateRequest(
            workspace_id=self.id,
            fullscreen_viewport_id="",
        )
        self._pb = self._client._workspace_stub.Update(req, metadata=self._client._grpc_metadata)

    def delete_viewport(self, viewport: Viewport) -> None:
        """Delete a viewport from this workspace."""
        self._client._workspace_stub.DeleteViewport(
            models.ResourceId(id=viewport.id), metadata=self._client._grpc_metadata
        )
