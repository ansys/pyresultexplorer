# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workspace entity class."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .. import models
from .base import NamedBaseEntity
from .viewport import Viewport

if TYPE_CHECKING:
    from .solution import View

RX_WORKSPACE_TEMPLATE_EXTENSION = ".rxwt"


class Workspace(NamedBaseEntity[models.Workspace]):
    """Represents a workspace with viewports and solutions."""

    @property
    def _sync_options(self):
        return self._pb.sync_options

    @property
    def sync_camera(self) -> bool:
        """Whether camera synchronization is enabled."""
        return self._sync_options.camera

    @sync_camera.setter
    def sync_camera(self, value: bool):
        self.set_sync(camera=value)

    @property
    def sync_time_freq(self) -> bool:
        """Whether time/frequency synchronization is enabled."""
        return self._sync_options.time_freq

    @sync_time_freq.setter
    def sync_time_freq(self, value: bool):
        self.set_sync(time_freq=value)

    @property
    def sync_legend(self) -> bool:
        """Whether legend synchronization is enabled."""
        return self._sync_options.legend

    @sync_legend.setter
    def sync_legend(self, value: bool):
        self.set_sync(legend=value)

    @property
    def sync_probe_entity(self) -> bool:
        """Whether probe entity synchronization is enabled."""
        return self._sync_options.probe_entity

    @sync_probe_entity.setter
    def sync_probe_entity(self, value: bool):
        self.set_sync(probe_entity=value)

    @property
    def sync_probe_location(self) -> bool:
        """Whether probe location synchronization is enabled."""
        return self._sync_options.probe_location

    @sync_probe_location.setter
    def sync_probe_location(self, value: bool):
        self.set_sync(probe_location=value)

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
        vp_response = self._client._workspace_stub.ListViewports(models.ResourceId(id=self.id))
        return [Viewport(v, self._client) for v in vp_response.viewports]

    def create_viewport(self, viewport: Viewport, direction, size: float = None) -> Viewport:
        """Create a new viewport as a child of the given viewport."""
        req = models.CreateViewportRequest(
            workspace_id=self.id,
            viewport_id=viewport.id,
            direction=direction,
            size=size,
        )
        pb_vp = self._client._workspace_stub.CreateViewport(req)
        return Viewport(pb_vp, self._client)

    def assign_view(self, view: View, wait: bool = True) -> Viewport:
        """Assign a view to the first viewport in this workspace."""
        first_viewport = self.viewports[0]
        return first_viewport.set_view(view, wait=wait)

    def set_sync(
        self,
        camera: bool | None = None,
        time_freq: bool | None = None,
        legend: bool | None = None,
        probe_entity: bool | None = None,
        probe_location: bool | None = None,
    ) -> None:
        """Update synchronization options for this workspace."""
        # Only update fields that are specified (partial update)
        sync_opts = models.SyncOptions()
        sync_opts.CopyFrom(self._pb.sync_options)

        if camera is not None:
            sync_opts.camera = camera
        if time_freq is not None:
            sync_opts.time_freq = time_freq
        if legend is not None:
            sync_opts.legend = legend
        if probe_entity is not None:
            sync_opts.probe_entity = probe_entity
        if probe_location is not None:
            sync_opts.probe_location = probe_location

        req = models.WorkspaceUpdateRequest(
            workspace_id=self.id,
            sync_options=sync_opts,
        )
        self._pb = self._client._workspace_stub.Update(req)

    def set_fullscreen_viewport(self, viewport: Viewport) -> None:
        """Set a viewport to fullscreen mode."""
        req = models.WorkspaceUpdateRequest(
            workspace_id=self.id,
            fullscreen_viewport_id=viewport.id,
        )
        self._pb = self._client._workspace_stub.Update(req)

    def exit_fullscreen(self) -> None:
        """Exit fullscreen mode."""
        req = models.WorkspaceUpdateRequest(
            workspace_id=self.id,
            fullscreen_viewport_id="",
        )
        self._pb = self._client._workspace_stub.Update(req)

    def delete_viewport(self, viewport: Viewport) -> None:
        """Delete a viewport from this workspace."""
        self._client._workspace_stub.DeleteViewport(models.ResourceId(id=viewport.id))
        # Refresh workspace data
        self._pb = self._client._workspace_stub.Get(models.ResourceId(id=self.id))

    def export_as_template(self, path: str | Path) -> None:
        """Save this workspace as a template file."""
        path = Path(path)
        if path.suffix != RX_WORKSPACE_TEMPLATE_EXTENSION:
            path = path.with_suffix(path.suffix + RX_WORKSPACE_TEMPLATE_EXTENSION)
        path.parent.mkdir(parents=True, exist_ok=True)
        req = models.ResourceId(id=self.id)
        template = self._client._workspace_stub.ExportWorkspace(req)
        with open(path, "w") as f:
            f.write(template.data)

    @classmethod
    def import_from_template(
        cls,
        client,
        path: str | Path,
        *,
        workspace_name: str,
        solutions: list[models.WorkspaceImportRequest.SolutionInfo],
        use_camera_position: bool | None = None,
        use_time_freq: bool | None = None,
        use_body_visibility: bool | None = None,
    ) -> Workspace:
        """Create a workspace by importing a template file.

        Parameters
        ----------
        client : Client
            The connected client.
        path : str | Path
            Path to the workspace template file (.rxwt).
        workspace_name : str
            Name for the new workspace.
        solutions : list[WorkspaceImportRequest.SolutionInfo]
            Solution bindings to use when importing. Each entry maps a slot in the
            template to a specific result provider and file path.
        use_camera_position : bool, optional
            Whether to restore the camera position from the template.
        use_time_freq : bool, optional
            Whether to restore the time/frequency setting from the template.
        use_body_visibility : bool, optional
            Whether to restore body visibility from the template.

        Returns
        -------
        Workspace
            The newly created workspace.

        """
        template_data = Path(path).read_text()
        kwargs = {
            "template": template_data,
            "workspace_name": workspace_name,
            "solutions": solutions,
        }
        if use_camera_position is not None:
            kwargs["use_camera_position"] = use_camera_position
        if use_time_freq is not None:
            kwargs["use_time_freq"] = use_time_freq
        if use_body_visibility is not None:
            kwargs["use_body_visibility"] = use_body_visibility
        req = models.WorkspaceImportRequest(**kwargs)
        resource_id = client._workspace_stub.ImportWorkspace(req)
        pb_ws = client._workspace_stub.Get(models.ResourceId(id=resource_id.id))
        return cls(pb_ws, client)
