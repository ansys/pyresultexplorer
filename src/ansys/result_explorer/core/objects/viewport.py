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
    """Wrapper for viewport metadata."""

    def __init__(self, pb_obj: models.Viewport, client: Client):
        self._pb_obj = pb_obj
        self._client = client

    def to_pb(self) -> models.Viewport:
        """Convert back for gRPC calls."""
        return self._pb_obj

    def __str__(self):
        # print as json-like string
        json_str = json.dumps(MessageToDict(self._pb_obj), indent=2)
        return json_str


class PlotViewportMetadata(ViewportMetadata):
    """Metadata specific to plot viewports."""

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


class MeshViewportMetadata(ViewportMetadata):
    """Metadata specific to mesh viewports."""

    @property
    def show_mesh_edges(self) -> bool:
        return self._pb_obj["showMeshEdges"]

    @show_mesh_edges.setter
    def show_mesh_edges(self, value: bool):
        self._pb_obj["showMeshEdges"] = value


class ChartViewportMetadata(ViewportMetadata):
    """Metadata specific to chart viewports."""

    pass


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
        view = self.view
        metadata = self._pb.metadata

        if view is None:
            return ViewportMetadata(metadata, self._client)

        if view.type == models.ViewType.VIEW_TYPE_PLOT:
            return PlotViewportMetadata(metadata, self._client)
        elif view.type == models.ViewType.VIEW_TYPE_CHART:
            return ChartViewportMetadata(metadata, self._client)
        elif view.type == models.ViewType.VIEW_TYPE_MESH:
            return MeshViewportMetadata(metadata, self._client)

        return ViewportMetadata(metadata, self._client)

    @property
    def size(self) -> float:
        return self._pb.size

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

    def set_metadata(self, metadata: ViewportMetadata) -> None:
        """Update metadata for this viewport."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            metadata=metadata.to_pb(),
            wait=True,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(
            req, metadata=self._client._grpc_metadata
        )

    def set_size(self, size: float) -> None:
        """Set the size of this viewport in the workspace layout."""
        req = models.UpdateViewportRequest(
            viewport_id=self.id,
            size=size,
            wait=False,
        )
        self._pb = self._client._workspace_stub.UpdateViewport(
            req, metadata=self._client._grpc_metadata
        )
