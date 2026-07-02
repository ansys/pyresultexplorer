# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
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

"""Chart definition objects."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

from ansys.result_explorer.core import models
from ansys.result_explorer.core.exceptions import ResultExplorerError

from .plot_definition import (
    Field,
    ResultType,
    ShellPosition,
    _custom_option_value,
    _proto_field_to_field,
)

_ProtoChart = TypeVar("_ProtoChart", models.ChartDefinition, models.ChartDefinitionCreate)


class Filter(str, Enum):
    """Filter applied to a chart result series."""

    min = "min"
    max = "max"
    average = "average"


@dataclass
class ChartResult:
    """Collects one or more result series in a chart definition."""

    result_type: ResultType
    name: str | None = None
    fields: list[Field] | None = field(default_factory=list)
    location: str | None = None
    average_by_entity: bool | None = False
    filters: list[Filter] | None = None
    mesh_scoping: models.NamedSelectionDefinition | None = None
    named_selection_id: str | None = None
    shell_position: ShellPosition | None = ShellPosition.top
    on_skin: bool | None = True


@dataclass
class ChartDefinition:
    """Defines a chart, including its results and display options."""

    name: str
    supports_monitoring: bool | None = None
    results: list[ChartResult] | None = field(default_factory=list)
    all_sets: bool | None = True
    set_ids: list[int] | None = None
    user_defined: bool | None = False
    script: str | None = None
    plotly_figure: bool | None = False
    mesh_scoping: models.NamedSelectionDefinition | None = None
    named_selection_id: str | None = None
    custom_options: dict[str, int | float | str | bool] | None = field(default_factory=dict)
    chunk_size: int | None = None
    id: str | None = None
    creation_time: str | None = None

    def to_proto(self, proto_type: type[_ProtoChart]) -> _ProtoChart:
        """Convert to a protobuf chart message."""
        return chart_definition_to_proto(self, proto_type)

    @classmethod
    def from_proto(
        cls, proto_chart: models.ChartDefinition | models.ChartDefinitionCreate
    ) -> "ChartDefinition":
        """Create a ChartDefinition from a protobuf chart message."""
        return proto_to_chart_definition(proto_chart)


def chart_result_to_proto(chart_result: ChartResult) -> models.ChartResult:
    """Convert a ChartResult to a protobuf message."""
    proto_cr = models.ChartResult()
    proto_cr.result_type = getattr(
        models.ResultType, f"RESULT_TYPE_{chart_result.result_type.name.upper()}"
    )
    if chart_result.name is not None:
        proto_cr.name = chart_result.name
    if chart_result.fields is not None:
        for f in chart_result.fields:
            proto_field = proto_cr.fields.add()
            proto_field.name = f.name.value
            if f.name.name.startswith("total_"):
                raise ResultExplorerError(
                    "PyResultExplorer is affected by a known issue when "
                    "creating or modifying charts with total result fields."
                )
            if f.components is not None:
                proto_field.components.extend([c.value for c in f.components])
    if chart_result.location is not None:
        proto_cr.location = chart_result.location
    if chart_result.average_by_entity is not None:
        proto_cr.average_by_entity = chart_result.average_by_entity
    if chart_result.filters is not None:
        proto_cr.filters.extend(
            [getattr(models.Filter, f"FILTER_{f.name.upper()}") for f in chart_result.filters]
        )
    if chart_result.mesh_scoping is not None:
        proto_cr.mesh_scoping.CopyFrom(chart_result.mesh_scoping)
    if chart_result.named_selection_id is not None:
        proto_cr.named_selection_id = chart_result.named_selection_id
    if chart_result.shell_position is not None:
        proto_cr.shell_position = getattr(
            models.ShellPosition,
            f"SHELL_POSITION_{chart_result.shell_position.name.upper()}",
        )
    if chart_result.on_skin is not None:
        proto_cr.on_skin = chart_result.on_skin
    return proto_cr


def proto_to_chart_result(proto_cr: models.ChartResult) -> ChartResult:
    """Convert a protobuf ChartResult message to a ChartResult."""
    result_type_name = models.ResultType.Name(proto_cr.result_type)
    result_type = ResultType(result_type_name.removeprefix("RESULT_TYPE_").lower())

    fields = [_proto_field_to_field(f) for f in proto_cr.fields]

    filters = None
    if proto_cr.filters:
        filters = [
            Filter(models.Filter.Name(f).removeprefix("FILTER_").lower()) for f in proto_cr.filters
        ]

    shell_position = None
    sp_name = models.ShellPosition.Name(proto_cr.shell_position)
    if sp_name:
        shell_position = ShellPosition(sp_name.removeprefix("SHELL_POSITION_").lower())

    mesh_scoping = proto_cr.mesh_scoping if proto_cr.HasField("mesh_scoping") else None

    return ChartResult(
        result_type=result_type,
        name=proto_cr.name or None,
        fields=fields,
        location=proto_cr.location or None,
        average_by_entity=proto_cr.average_by_entity,
        filters=filters,
        mesh_scoping=mesh_scoping,
        named_selection_id=proto_cr.named_selection_id or None,
        shell_position=shell_position,
        on_skin=proto_cr.on_skin,
    )


def chart_definition_to_proto(
    chart_definition: ChartDefinition, proto_type: type[_ProtoChart]
) -> _ProtoChart:
    """Convert a ChartDefinition to a protobuf message."""
    proto_chart = proto_type()
    if chart_definition.name is not None:
        proto_chart.name = chart_definition.name
    if chart_definition.id is not None:
        proto_chart.id = chart_definition.id
    if chart_definition.results is not None:
        for result in chart_definition.results:
            proto_result = proto_chart.results.add()
            proto_result.CopyFrom(chart_result_to_proto(result))
    if chart_definition.all_sets is not None:
        proto_chart.all_sets = chart_definition.all_sets
    if chart_definition.set_ids is not None:
        proto_chart.set_ids.extend(chart_definition.set_ids)
    if chart_definition.user_defined is not None:
        proto_chart.user_defined = chart_definition.user_defined
    if chart_definition.script is not None:
        proto_chart.script = chart_definition.script
    if chart_definition.plotly_figure is not None:
        proto_chart.plotly_figure = chart_definition.plotly_figure
    if chart_definition.mesh_scoping is not None:
        proto_chart.mesh_scoping.CopyFrom(chart_definition.mesh_scoping)
    if chart_definition.named_selection_id is not None:
        proto_chart.named_selection_id = chart_definition.named_selection_id
    if chart_definition.custom_options is not None:
        for key, value in chart_definition.custom_options.items():
            cov = models.CustomOptionsValue()
            if isinstance(value, bool):
                cov.bool = value
            elif isinstance(value, int):
                cov.int32 = value
            elif isinstance(value, float):
                cov.float = value
            elif isinstance(value, str):
                cov.string = value
            else:
                raise ValueError(f"Unsupported custom option type: {type(value)}")
            proto_chart.custom_options[key].CopyFrom(cov)
    if chart_definition.chunk_size is not None:
        proto_chart.chunk_size = chart_definition.chunk_size
    return proto_chart


def proto_to_chart_definition(
    proto_chart: models.ChartDefinition | models.ChartDefinitionCreate,
) -> ChartDefinition:
    """Convert a protobuf chart message to a ChartDefinition."""
    results = [proto_to_chart_result(r) for r in proto_chart.results]
    custom_options = {k: _custom_option_value(v) for k, v in proto_chart.custom_options.items()}
    mesh_scoping = proto_chart.mesh_scoping if proto_chart.HasField("mesh_scoping") else None
    chunk_size = proto_chart.chunk_size if proto_chart.HasField("chunk_size") else None

    return ChartDefinition(
        name=proto_chart.name,
        supports_monitoring=getattr(proto_chart, "supports_monitoring", None),
        results=results,
        all_sets=proto_chart.all_sets,
        set_ids=list(proto_chart.set_ids) or None,
        user_defined=proto_chart.user_defined,
        script=proto_chart.script or None,
        plotly_figure=proto_chart.plotly_figure,
        mesh_scoping=mesh_scoping,
        named_selection_id=proto_chart.named_selection_id or None,
        custom_options=custom_options or None,
        chunk_size=chunk_size,
        id=proto_chart.id or None,
        creation_time=getattr(proto_chart, "creation_time", None) or None,
    )
