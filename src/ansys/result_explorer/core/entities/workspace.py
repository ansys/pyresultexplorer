"""Workspace entity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import models
from .base import BaseEntity
from .viewport import Viewport

if TYPE_CHECKING:
    from .solution import Solution
    from .view import View


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
        # Refresh workspace data
        self._pb = self._client._workspace_stub.Get(
            models.ResourceId(id=self.id), metadata=self._client._grpc_metadata
        )
