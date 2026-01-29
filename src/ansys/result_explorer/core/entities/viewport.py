"""Viewport entity and metadata classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import models
from .base import BaseEntity

if TYPE_CHECKING:
    from ..client import Client
    from .solution import Solution, View


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
