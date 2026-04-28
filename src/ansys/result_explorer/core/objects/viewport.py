"""Viewport entity and metadata classes."""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Literal

from google.protobuf.json_format import MessageToDict

from .. import models
from .base import BaseEntity

if TYPE_CHECKING:
    from ..client import Client
    from .solution import View


class CameraPosition:
    """Human-readable wrapper for a 4x4 camera matrix.

    The matrix is stored row-major as 16 values::

        [ right.x   right.y   right.z   tx ]
        [ up.x      up.y      up.z      ty ]
        [ fwd.x     fwd.y     fwd.z     tz ]
        [ 0         0         0         w  ]
    """

    def __init__(self, matrix: list[float]):
        if len(matrix) != 16:
            raise ValueError(f"Expected 16 matrix values, got {len(matrix)}")
        self._m = matrix

    @property
    def matrix(self) -> list[float]:
        """Raw 16-element row-major matrix."""
        return list(self._m)

    @property
    def right(self) -> tuple[float, float, float]:
        """Camera right (X-axis) direction."""
        return (self._m[0], self._m[1], self._m[2])

    @property
    def up(self) -> tuple[float, float, float]:
        """Camera up (Y-axis) direction."""
        return (self._m[4], self._m[5], self._m[6])

    @property
    def forward(self) -> tuple[float, float, float]:
        """Camera forward (Z-axis) direction."""
        return (self._m[8], self._m[9], self._m[10])

    @property
    def zoom(self) -> float:
        """Zoom / scale factor stored in matrix[15]."""
        return self._m[15]

    @property
    def translation(self) -> tuple[float, float, float]:
        """Camera translation (tx, ty, tz) stored in matrix[3], [7], [11]."""
        return (self._m[3], self._m[7], self._m[11])

    def with_zoom(self, zoom: float) -> CameraPosition:
        """Return a copy of this CameraPosition with a new zoom value."""
        new_m = list(self._m)
        new_m[15] = zoom
        return CameraPosition(new_m)

    def with_translation(self, tx: float, ty: float, tz: float) -> CameraPosition:
        """Return a copy of this CameraPosition with new translation values."""
        new_m = list(self._m)
        new_m[3] = tx
        new_m[7] = ty
        new_m[11] = tz
        return CameraPosition(new_m)

    def __repr__(self) -> str:
        return (
            f"CameraPosition(right={self.right}, up={self.up}, forward={self.forward},"
            f" zoom={self.zoom}, translation={self.translation})"
        )

    # ------------------------------------------------------------------
    # Axis-aligned factory methods
    # ------------------------------------------------------------------

    @classmethod
    def _from_axes(
        cls,
        right: tuple[float, float, float],
        up: tuple[float, float, float],
        forward: tuple[float, float, float],
    ) -> CameraPosition:
        m = [0.0] * 16
        m[0], m[1], m[2] = right
        m[4], m[5], m[6] = up
        m[8], m[9], m[10] = forward
        m[15] = 1.0
        return cls(m)

    @classmethod
    def top(cls) -> CameraPosition:
        """View parallel to XZ plane, looking from +Y (Ansys Mechanical convention)."""
        return cls._from_axes((1, 0, 0), (0, 0, 1), (0, 1, 0))

    @classmethod
    def bottom(cls) -> CameraPosition:
        """View parallel to XZ plane, looking from -Y (Ansys Mechanical convention)."""
        return cls._from_axes((-1, 0, 0), (0, 0, 1), (0, -1, 0))

    @classmethod
    def front(cls) -> CameraPosition:
        """View parallel to XY plane, looking from +Z (Ansys Mechanical convention)."""
        return cls._from_axes((1, 0, 0), (0, 1, 0), (0, 0, 1))

    @classmethod
    def back(cls) -> CameraPosition:
        """View parallel to XY plane, looking from -Z (Ansys Mechanical convention)."""
        return cls._from_axes((-1, 0, 0), (0, 1, 0), (0, 0, -1))

    @classmethod
    def left(cls) -> CameraPosition:
        """View parallel to YZ plane, looking from -X (Ansys Mechanical convention)."""
        return cls._from_axes((0, 0, 1), (0, 1, 0), (-1, 0, 0))

    @classmethod
    def right_view(cls) -> CameraPosition:
        """View parallel to YZ plane, looking from +X (Ansys Mechanical convention)."""
        return cls._from_axes((0, 0, -1), (0, 1, 0), (1, 0, 0))

    @classmethod
    def isometric(cls) -> CameraPosition:
        """Standard isometric view (+X+Y+Z corner, Y up).

        Axes derived from camera looking toward origin from (1,1,1):
          right   = normalize(cross(look, worldUp)) = (1/√2, 0, -1/√2)
          up      = normalize(cross(right, look))   = (-1/√6, 2/√6, -1/√6)
          forward = (1/√3, 1/√3, 1/√3)
        """
        s2 = math.sqrt(2) / 2
        s3 = math.sqrt(3) / 3
        s6 = math.sqrt(6) / 6
        return cls._from_axes(
            (s2, 0, -s2),
            (-s6, 2 * s6, -s6),
            (s3, s3, s3),
        )

    # ------------------------------------------------------------------
    # Rotation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mat3_mul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
        """Multiply two 3x3 matrices stored as 9-element tuples (row-major)."""
        return tuple(
            sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3)) for r in range(3) for c in range(3)
        )

    def rotate_x(self, degrees: float) -> CameraPosition:
        """Return a new CameraPosition rotated *degrees* around the world X axis."""
        return self._rotate(degrees, axis="x")

    def rotate_y(self, degrees: float) -> CameraPosition:
        """Return a new CameraPosition rotated *degrees* around the world Y axis."""
        return self._rotate(degrees, axis="y")

    def rotate_z(self, degrees: float) -> CameraPosition:
        """Return a new CameraPosition rotated *degrees* around the world Z axis."""
        return self._rotate(degrees, axis="z")

    def _rotate(self, degrees: float, axis: Literal["x", "y", "z"]) -> CameraPosition:
        a = math.radians(degrees)
        c, s = math.cos(a), math.sin(a)

        if axis == "x":
            rot = (1, 0, 0, 0, c, -s, 0, s, c)
        elif axis == "y":
            rot = (c, 0, s, 0, 1, 0, -s, 0, c)
        else:  # z
            rot = (c, -s, 0, s, c, 0, 0, 0, 1)

        # Extract current 3x3 rotation from the matrix (rows 0-2, cols 0-2)
        cur = (
            self._m[0],
            self._m[1],
            self._m[2],
            self._m[4],
            self._m[5],
            self._m[6],
            self._m[8],
            self._m[9],
            self._m[10],
        )
        new_rot = self._mat3_mul(rot, cur)

        new_m = list(self._m)
        new_m[0], new_m[1], new_m[2] = new_rot[0], new_rot[1], new_rot[2]
        new_m[4], new_m[5], new_m[6] = new_rot[3], new_rot[4], new_rot[5]
        new_m[8], new_m[9], new_m[10] = new_rot[6], new_rot[7], new_rot[8]
        return CameraPosition(new_m)


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


class ThreeDViewportMetadata(ViewportMetadata):
    """Metadata specific to 3D viewports."""

    @property
    def show_mesh_edges(self) -> bool:
        return self._pb_obj["showMeshEdges"]

    @show_mesh_edges.setter
    def show_mesh_edges(self, value: bool):
        self._pb_obj["showMeshEdges"] = value

    @property
    def explode(self) -> bool:
        return self._pb_obj["explodeSettings"]["active"]

    @explode.setter
    def explode(self, value: bool):
        self._pb_obj["explodeSettings"]["active"] = value

    @property
    def explode_scale_factor(self) -> float:
        return self._pb_obj["explodeSettings"]["scaleFactor"]

    @explode_scale_factor.setter
    def explode_scale_factor(self, value: float):
        self._pb_obj["explodeSettings"]["scaleFactor"] = value

    @property
    def explode_direction(self) -> Literal["Radial", "X", "Y", "Z"]:
        return self._pb_obj["explodeSettings"]["direction"]

    @explode_direction.setter
    def explode_direction(self, value: Literal["Radial", "X", "Y", "Z"]):
        self._pb_obj["explodeSettings"]["direction"] = value

    @property
    def expanded_groups(self) -> list[str]:
        return self._pb_obj["expandedGroups"]

    @expanded_groups.setter
    def expanded_groups(self, value: list[str]):
        self._pb_obj["expandedGroups"] = value

    @property
    def visible_bodies(self) -> list[str]:
        return self._pb_obj["shownBodies"]

    @visible_bodies.setter
    def visible_bodies(self, value: list[str]):
        self._pb_obj["shownBodies"] = value

    @property
    def camera_position(self) -> CameraPosition | None:
        """Current camera position, or None if not set."""
        if "cameraPosition" not in self._pb_obj:
            return None
        raw = self._pb_obj["cameraPosition"]
        return CameraPosition(list(raw["matrix"]))

    @camera_position.setter
    def camera_position(self, value: CameraPosition) -> None:
        self._pb_obj["cameraPosition"] = {"matrix": value.matrix}


class MeshViewportMetadata(ThreeDViewportMetadata):
    """Metadata specific to mesh viewports."""

    pass


class PlotViewportMetadata(ThreeDViewportMetadata):
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

    @property
    def deformation_scale(self) -> float:
        return self._pb_obj["deformationScale"]

    @deformation_scale.setter
    def deformation_scale(self, value: float):
        self._pb_obj["deformationScale"] = value


class ChartViewportMetadata(ViewportMetadata):
    """Metadata specific to chart viewports."""

    pass


class ConvergenceTrackersViewportMetadata(ViewportMetadata):
    """Metadata specific to convergence trackers viewports."""

    @property
    def selected_tracker_name(self) -> str:
        return self._pb_obj["selectedTrackerName"]

    @selected_tracker_name.setter
    def selected_tracker_name(self, value: str):
        self._pb_obj["selectedTrackerName"] = value


class ContactTrackersViewportMetadata(ViewportMetadata):
    """Metadata specific to contact trackers viewports."""

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
        elif view.type == models.ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS:
            return ConvergenceTrackersViewportMetadata(metadata, self._client)
        elif view.type == models.ViewType.VIEW_TYPE_CONTACT_TRACKERS:
            return ContactTrackersViewportMetadata(metadata, self._client)

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

    def take_snapshot(self, settings: models.SnapshotSettings | None = None) -> bytes:
        """Take a snapshot of this viewport.

        Parameters
        ----------
        settings : SnapshotSettings, optional
            Snapshot settings to control what elements appear in the image
            (timestamp, logo, legend, solution name, etc.). If None, uses server defaults.

        Returns
        -------
        bytes
            PNG image data.
        """
        req = models.CreateSnapshotRequest(viewport_id=self.id)
        if settings is not None:
            req.settings.CopyFrom(settings)
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
