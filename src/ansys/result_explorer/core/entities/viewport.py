"""Viewport entity and metadata classes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from google.protobuf.json_format import MessageToDict

from .. import models
from .base import BaseEntity

if TYPE_CHECKING:
    from ..client import Client
    from .solution import View


class ViewportMetadata:
    """Wrapper for viewport metadata.

    Will need to be expanded and specialized to the different view types.
    """

    def __init__(self, pb_obj: models.Viewport, client: Client):
        self._pb_obj = pb_obj
        self._client = client

    @property
    def show_mesh_edges(self) -> bool:
        return self._pb_obj["showMeshEdges"]

    @show_mesh_edges.setter
    def show_mesh_edges(self, value: bool):
        self._pb_obj["showMeshEdges"] = value

    @property
    def show_min_max_labels(self) -> bool:
        return self._pb_obj["showMinMaxLabels"]

    @show_min_max_labels.setter
    def show_min_max_labels(self, value: bool):
        self._pb_obj["showMinMaxLabels"] = value

    def to_pb(self) -> models.Viewport:
        """Convert back for gRPC calls."""
        return self._pb_obj

    def __str__(self):
        # print as json-like string
        json_str = json.dumps(MessageToDict(self._pb_obj), indent=2)
        return json_str


class Viewport(BaseEntity[models.Viewport]):
    """Represents a viewport in a workspace."""

    @property
    def solution_id(self) -> str | None:
        """ID of the solution assigned to this viewport."""
        return self._pb.solution_id

    @property
    def view_id(self) -> str | None:
        """ID of the view assigned to this viewport."""
        return self._pb.view_id

    @property
    def ready(self) -> bool:
        """Whether the viewport is ready."""
        return self._pb.ready

    @property
    def metadata(self) -> ViewportMetadata:
        """Access viewport metadata."""
        return ViewportMetadata(self._pb.metadata, self._client)

    @property
    def view(self) -> View | None:
        """Get the assigned view, if any."""
        # todo: we could cache this

        if self.view_id and self.solution_id:
            solution = self._client.get_solution(self.solution_id)
            view = next((v for v in solution.views if v.id == self.view_id), None)
            return view
        return None

    def set_view(self, view: View, wait: bool = True) -> Viewport:
        """Assign a view to this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            solution_id=view.solution.id,
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

    def modify_view_metadata(self, metadata: ViewportMetadata) -> None:
        """Update metadata for this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            metadata=metadata.to_pb(),
            wait=True,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(
            req, metadata=self._client._grpc_metadata
        )
