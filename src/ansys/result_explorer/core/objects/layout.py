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

"""Workspace viewport layout description."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import models

if TYPE_CHECKING:
    from .viewport import Viewport
    from .workspace import Workspace

_CELL_WIDTH = 22
_CELL_HEIGHT = 4


@dataclass(frozen=True)
class ViewportPlacement:
    """Position of a viewport inside a workspace layout."""

    viewport: Viewport
    """Viewport placed at this position."""

    row: int
    """Zero-based index of the topmost row occupied by the viewport."""

    column: int
    """Zero-based index of the leftmost column occupied by the viewport."""

    row_span: int
    """Number of rows the viewport spans."""

    column_span: int
    """Number of columns the viewport spans."""

    x: float
    """Left edge of the viewport, as a fraction of the workspace width."""

    y: float
    """Top edge of the viewport, as a fraction of the workspace height."""

    width: float
    """Viewport width, as a fraction of the workspace width."""

    height: float
    """Viewport height, as a fraction of the workspace height."""

    def covers(self, row: int, column: int) -> bool:
        """Return whether the viewport occupies a grid cell.

        Parameters
        ----------
        row : int
            Zero-based row index.
        column : int
            Zero-based column index.

        Returns
        -------
        bool
            ``True`` if the cell is occupied by this viewport.

        Examples
        --------
        Check whether a placement occupies the upper-left cell.

        >>> placement.covers(row=0, column=0)
        True

        """
        return (
            self.row <= row < self.row + self.row_span
            and self.column <= column < self.column + self.column_span
        )


class WorkspaceLayout:
    """Describes how viewports are arranged in a workspace.

    Every layout is described as a grid of rows and columns. Viewports
    that are not part of a regular grid span several rows or columns.

    Examples
    --------
    Print the arrangement of the viewports in a workspace.

    >>> print(workspace.layout)

    """

    def __init__(self, placements: list[ViewportPlacement], rows: int, cols: int):
        """Initialize a workspace layout."""
        self._placements = placements
        self._rows = rows
        self._cols = cols

    @property
    def placements(self) -> list[ViewportPlacement]:
        """Placement of each viewport, ordered from top to bottom and left to right."""
        return list(self._placements)

    @property
    def grid_shape(self) -> tuple[int, int]:
        """Number of rows and columns spanned by the layout."""
        return self._rows, self._cols

    @property
    def is_grid(self) -> bool:
        """Whether every viewport occupies exactly one cell."""
        return all(p.row_span == 1 and p.column_span == 1 for p in self._placements)

    def placement_of(self, viewport: Viewport | str) -> ViewportPlacement:
        """Return the placement of a viewport.

        Parameters
        ----------
        viewport : Viewport or str
            Viewport or viewport ID to locate.

        Returns
        -------
        ViewportPlacement
            Placement of the requested viewport.

        Raises
        ------
        KeyError
            If the viewport is not part of this layout.

        Examples
        --------
        Get the grid position of a viewport.

        >>> placement = workspace.layout.placement_of(viewport)
        >>> placement.row, placement.column
        (0, 1)

        """
        viewport_id = viewport if isinstance(viewport, str) else viewport.id
        for placement in self._placements:
            if placement.viewport.id == viewport_id:
                return placement
        raise KeyError(f"Viewport {viewport_id} is not part of this workspace layout.")

    def viewport_at(self, row: int, column: int) -> Viewport:
        """Return the viewport occupying a grid cell.

        A viewport that spans several cells is returned for each cell
        that it occupies.

        Parameters
        ----------
        row : int
            Zero-based row index, from top to bottom.
        column : int
            Zero-based column index, from left to right.

        Returns
        -------
        Viewport
            Viewport occupying the requested cell.

        Raises
        ------
        IndexError
            If the cell is outside the layout.

        Examples
        --------
        Get the viewport in the second row of the first column.

        >>> viewport = workspace.layout.viewport_at(row=1, column=0)

        """
        for placement in self._placements:
            if placement.covers(row, column):
                return placement.viewport
        raise IndexError(
            f"No viewport at row {row}, column {column} in a {self._rows}x{self._cols} layout."
        )

    def describe(self) -> str:
        """Return a diagram of the viewport arrangement.

        Returns
        -------
        str
            Text diagram followed by a legend of viewport IDs.

        Examples
        --------
        Show where each viewport is positioned.

        >>> print(workspace.layout.describe())

        """
        canvas = _blank_canvas(self._rows, self._cols)
        for index, placement in enumerate(self._placements):
            _draw_placement(canvas, index, placement)

        diagram = "\n".join("".join(line).rstrip() for line in canvas)
        legend = "\n".join(
            f"[{index}] {placement.viewport.id} "
            f"(row {placement.row}, column {placement.column}, "
            f"{placement.row_span}x{placement.column_span} cells)"
            for index, placement in enumerate(self._placements)
        )
        return f"{diagram}\n{legend}"

    def __str__(self) -> str:
        """Return a diagram of the viewport arrangement."""
        return self.describe()


def _blank_canvas(rows: int, cols: int) -> list[list[str]]:
    width = cols * _CELL_WIDTH + 1
    height = rows * _CELL_HEIGHT + 1
    return [[" "] * width for _ in range(height)]


def _draw_placement(canvas: list[list[str]], index: int, placement: ViewportPlacement) -> None:
    left = placement.column * _CELL_WIDTH
    right = (placement.column + placement.column_span) * _CELL_WIDTH
    top = placement.row * _CELL_HEIGHT
    bottom = (placement.row + placement.row_span) * _CELL_HEIGHT

    for x in range(left, right + 1):
        canvas[top][x] = "-"
        canvas[bottom][x] = "-"
    for y in range(top, bottom + 1):
        canvas[y][left] = "|"
        canvas[y][right] = "|"
    for y, x in ((top, left), (top, right), (bottom, left), (bottom, right)):
        canvas[y][x] = "+"

    label = f"[{index}] r{placement.row}c{placement.column}"[: right - left - 3]
    for offset, character in enumerate(label):
        canvas[top + 1][left + 2 + offset] = character


def _child_fractions(sizes: list[float] | None, count: int) -> list[float]:
    if not sizes or len(sizes) != count:
        return [1.0 / count] * count
    total = sum(sizes)
    if total <= 0:
        return [1.0 / count] * count
    return [size / total for size in sizes]


def _collect_rects(
    nodes: dict,
    node_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    rects: dict[str, tuple[float, float, float, float]],
) -> None:
    node = nodes[node_id]
    children = node.get("childNodes")
    if not children:
        rects[node["portalId"]] = (x, y, width, height)
        return

    fractions = _child_fractions(node.get("sizes"), len(children))
    offset = 0.0
    horizontal = node.get("direction") == "horizontal"
    for child_id, fraction in zip(children, fractions, strict=True):
        if horizontal:
            _collect_rects(nodes, child_id, x + offset * width, y, fraction * width, height, rects)
        else:
            _collect_rects(nodes, child_id, x, y + offset * height, width, fraction * height, rects)
        offset += fraction


def _edge_index(edges: list[float], value: float) -> int:
    return min(range(len(edges)), key=lambda i: abs(edges[i] - value))


def _build_layout(workspace: Workspace) -> WorkspaceLayout:
    """Build the layout of a workspace from its exported template."""
    template = workspace._client._workspace_stub.ExportWorkspace(models.ResourceId(id=workspace.id))
    state = json.loads(template.data)["app_state"]
    workspace_states = state["workspaces"]
    workspace_state = workspace_states.get(workspace.id) or next(iter(workspace_states.values()))

    rects: dict[str, tuple[float, float, float, float]] = {}
    _collect_rects(
        state["viewportLayoutNodes"],
        workspace_state["rootViewportLayoutNodeId"],
        0.0,
        0.0,
        1.0,
        1.0,
        rects,
    )

    x_edges = sorted({rect[0] for rect in rects.values()} | {1.0})
    y_edges = sorted({rect[1] for rect in rects.values()} | {1.0})

    viewports = {viewport.id: viewport for viewport in workspace.viewports}
    placements = []
    for viewport_id, (x, y, width, height) in rects.items():
        column = _edge_index(x_edges, x)
        row = _edge_index(y_edges, y)
        placements.append(
            ViewportPlacement(
                viewport=viewports[viewport_id],
                row=row,
                column=column,
                row_span=_edge_index(y_edges, y + height) - row,
                column_span=_edge_index(x_edges, x + width) - column,
                x=x,
                y=y,
                width=width,
                height=height,
            )
        )

    placements.sort(key=lambda p: (p.row, p.column))
    return WorkspaceLayout(placements, rows=len(y_edges) - 1, cols=len(x_edges) - 1)
