"""Pythonic wrapper objects for gRPC models."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client

from . import models


class BaseEntity:
    """Base class for all domain objects wrapping protobuf messages."""

    def __init__(self, pb_obj, client: Client):
        self._pb = pb_obj
        self._client = client

    @property
    def id(self) -> str:
        """Unique identifier."""
        return self._pb.id

    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._pb.name if hasattr(self._pb, "name") else ""


class View(BaseEntity):
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


class Viewport(BaseEntity):
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


class Solution(BaseEntity):
    """Represents a solution loaded in the server."""

    @property
    def views(self) -> list[View]:
        """List of views available in this solution."""
        return [View(v, self._client) for v in self._pb.views]

    def delete(self) -> None:
        """Delete this solution from the server."""
        self._client._solution_stub.Delete(
            models.ResourceId(id=self.id), metadata=self._client._grpc_metadata
        )


class Workspace(BaseEntity):
    """Represents a workspace with viewports and solutions."""

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
