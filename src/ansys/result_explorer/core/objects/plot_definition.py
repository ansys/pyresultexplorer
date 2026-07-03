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

"""Plot definition objects."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

from ansys.result_explorer.core import models
from ansys.result_explorer.core.exceptions import ResultExplorerError

_ProtoPlot = TypeVar("_ProtoPlot", models.PlotDefinition, models.PlotDefinitionCreate)


class ResultType(str, Enum):
    """Result types for plots and charts in Result Explorer."""

    displacement = "displacement"
    stress = "stress"
    nodal_stress = "nodal_stress"
    elastic_strain = "elastic_strain"
    nodal_elastic_strain = "nodal_elastic_strain"
    plastic_strain = "plastic_strain"
    nodal_plastic_strain = "nodal_plastic_strain"
    equivalent_nodal_plastic_strain = "equivalent_nodal_plastic_strain"
    temperature = "temperature"
    heat_flux = "heat_flux"
    equivalent_plastic_strain = "equivalent_plastic_strain"
    velocity = "velocity"
    acceleration = "acceleration"
    user_defined = "user_defined"
    global_energy = "global_energy"
    contact = "contact"
    failure = "failure"
    electric_potential = "electric_potential"
    electric_field = "electric_field"
    electric_flux_density = "electric_flux_density"
    newton_raphson_residual = "newton_raphson_residual"
    structural_temperature = "structural_temperature"
    thermal_strain = "thermal_strain"
    strain_energy = "strain_energy"
    kinetic_energy = "kinetic_energy"
    beam_results = "beam_results"


class ResultFieldName(str, Enum):
    """Field names for result types in Result Explorer."""

    total_displacement = "total_displacement"
    displacement = "displacement"

    stress_tensor = "stress_tensor"
    stress_tensor_global = "stress_tensor_global"
    stress_tensor_fiber = "stress_tensor_fiber"
    equivalent_von_mises_stress = "equivalent_von_mises_stress"

    principal_stress = "principal_stress"
    principal_stress_1 = "principal_stress_1"
    principal_stress_2 = "principal_stress_2"
    principal_stress_3 = "principal_stress_3"

    elastic_strain_tensor = "elastic_strain_tensor"
    elastic_strain_tensor_global = "elastic_strain_tensor_global"
    elastic_strain_tensor_fiber = "elastic_strain_tensor_fiber"
    equivalent_elastic_strain = "equivalent_elastic_strain"
    principal_elastic_strain = "principal_elastic_strain"
    principal_elastic_strain_1 = "principal_elastic_strain_1"
    principal_elastic_strain_2 = "principal_elastic_strain_2"
    principal_elastic_strain_3 = "principal_elastic_strain_3"

    equivalent_plastic_strain = "equivalent_plastic_strain"

    temperature = "temperature"
    heat_flux = "heat_flux"
    total_heat_flux = "total_heat_flux"

    velocity = "velocity"
    total_velocity = "total_velocity"

    acceleration = "acceleration"
    total_acceleration = "total_acceleration"

    global_kinetic_energy = "global_kinetic_energy"
    global_internal_energy = "global_internal_energy"
    global_total_energy = "global_total_energy"
    global_hourglass_energy = "global_hourglass_energy"

    contact_status = "contact_status"
    contact_pressure = "contact_pressure"
    contact_penetration = "contact_penetration"
    contact_sliding_distance = "contact_sliding_distance"
    contact_gap_distance = "contact_gap_distance"
    contact_friction_stress = "contact_friction_stress"
    contact_total_stress = "contact_total_stress"
    contact_fluid_penetration_pressure = "contact_fluid_penetration_pressure"
    contact_surface_heat_flux = "contact_surface_heat_flux"

    failure = "failure"

    total_force = "total_force"
    total_moment = "total_moment"

    electric_potential = "electric_potential"
    electric_field = "electric_field"
    total_electric_field = "total_electric_field"
    electric_flux_density = "electric_flux_density"
    total_electric_flux_density = "total_electric_flux_density"

    structural_temperature = "structural_temperature"
    thermal_strain = "thermal_strain"

    strain_energy = "strain_energy"
    kinetic_energy = "kinetic_energy"

    beam_axial_force = "beam_axial_force"
    beam_bending_moment_y = "beam_bending_moment_y"
    beam_bending_moment_z = "beam_bending_moment_z"
    beam_torsional_moment = "beam_torsional_moment"
    beam_axial_stress = "beam_axial_stress"
    beam_axial_strain = "beam_axial_strain"
    beam_shear_force_y = "beam_shear_force_y"
    beam_shear_force_z = "beam_shear_force_z"


class Component(str, Enum):
    """Components for result fields in Result Explorer."""

    X = "X"
    Y = "Y"
    Z = "Z"
    P1 = "1"
    P2 = "2"
    P3 = "3"
    XX = "XX"
    YY = "YY"
    ZZ = "ZZ"
    XY = "XY"
    YZ = "YZ"
    XZ = "XZ"


class Location(str, Enum):
    """Result locations for plots and charts in Result Explorer."""

    nodal = "Nodal"
    elemental = "Elemental"


@dataclass
class Field:
    """Result field definition for plots and charts in Result Explorer."""

    name: ResultFieldName
    components: list[Component] | None = None


class ShellPosition(str, Enum):
    """Shell position."""

    top = "top"
    middle = "middle"
    bottom = "bottom"
    all = "all"


@dataclass
class PlotDefinition:
    """Definition of a plot in Result Explorer."""

    result_type: ResultType
    location: str
    name: str | None = None
    fields: list[Field] | None = field(default_factory=list)
    average_by_entity: bool | None = False
    as_linear: bool | None = True
    on_skin: bool | None = True
    mesh_scoping: models.NamedSelectionDefinition | None = None
    named_selection_id: str | None = None
    # custom_selections: list[CustomSelection] | None = None
    set_ids: list[int] | None = None
    all_sets: bool | None = False
    last_set: bool | None = True
    script: str | None = None
    custom_options: dict[str, int | float | str | bool] | None = field(default_factory=dict)
    include_displacement: bool | None = False
    shell_position: ShellPosition | None = ShellPosition.top
    id: str | None = None
    creation_time: str | None = None
    supports_monitoring: bool | None = None

    def to_proto(self, proto_type: type[_ProtoPlot]) -> _ProtoPlot:
        """Convert to a protobuf plot message."""
        return plot_definition_to_proto(self, proto_type)

    @classmethod
    def from_proto(
        cls, proto_plot: models.PlotDefinition | models.PlotDefinitionCreate
    ) -> "PlotDefinition":
        """Create a PlotDefinition from a protobuf plot message."""
        return proto_to_plot_definition(proto_plot)


def plot_definition_to_proto(
    plot_definition: PlotDefinition, proto_type: type[_ProtoPlot]
) -> _ProtoPlot:
    """Convert a PlotDefinition to a protobuf message."""
    proto_plot = proto_type()
    proto_plot.result_type = getattr(
        models.ResultType, f"RESULT_TYPE_{plot_definition.result_type.name.upper()}"
    )
    proto_plot.location = plot_definition.location
    if plot_definition.id is not None:
        proto_plot.id = plot_definition.id
    if plot_definition.name is not None:
        proto_plot.name = plot_definition.name
    if plot_definition.fields is not None:
        for field in plot_definition.fields:
            proto_field = proto_plot.fields.add()
            proto_field.name = field.name.value
            if field.name.name.startswith("total_"):
                raise ResultExplorerError(
                    "PyResultExplorer is affected by a known issue when "
                    "creating or modifying plots with total result fields."
                )
            if field.components is not None:
                proto_field.components.extend([c.value for c in field.components])
    if plot_definition.average_by_entity is not None:
        proto_plot.average_by_entity = plot_definition.average_by_entity
    if plot_definition.as_linear is not None:
        proto_plot.as_linear = plot_definition.as_linear
    if plot_definition.on_skin is not None:
        proto_plot.on_skin = plot_definition.on_skin
    if plot_definition.mesh_scoping is not None:
        proto_plot.mesh_scoping.CopyFrom(plot_definition.mesh_scoping)
    if plot_definition.named_selection_id is not None:
        proto_plot.named_selection_id = plot_definition.named_selection_id
    if plot_definition.set_ids is not None:
        proto_plot.set_ids.extend(plot_definition.set_ids)
    if plot_definition.all_sets is not None:
        proto_plot.all_sets = plot_definition.all_sets
    if plot_definition.last_set is not None:
        proto_plot.last_set = plot_definition.last_set
    if plot_definition.script is not None:
        proto_plot.script = plot_definition.script
    if plot_definition.custom_options is not None:
        for key, value in plot_definition.custom_options.items():
            custom_option_value = models.CustomOptionsValue()
            if isinstance(value, bool):
                custom_option_value.bool = value
            elif isinstance(value, int):
                custom_option_value.int32 = value
            elif isinstance(value, float):
                custom_option_value.float = value
            elif isinstance(value, str):
                custom_option_value.string = value
            else:
                raise ValueError(f"Unsupported type for custom option value: {type(value)}")
            proto_plot.custom_options[key].CopyFrom(custom_option_value)
    if plot_definition.include_displacement is not None:
        proto_plot.include_displacement = plot_definition.include_displacement
    if plot_definition.shell_position is not None:
        proto_plot.shell_position = getattr(
            models.ShellPosition,
            f"SHELL_POSITION_{plot_definition.shell_position.name.upper()}",
        )

    return proto_plot


def proto_to_plot_definition(
    proto_plot: models.PlotDefinition | models.PlotDefinitionCreate,
) -> PlotDefinition:
    """Convert a protobuf plot message to a PlotDefinition."""
    result_type_name = models.ResultType.Name(proto_plot.result_type)
    result_type = ResultType(result_type_name.removeprefix("RESULT_TYPE_").lower())

    fields = [_proto_field_to_field(f) for f in proto_plot.fields]

    shell_position = None
    sp_name = models.ShellPosition.Name(proto_plot.shell_position)
    if sp_name:
        shell_position = ShellPosition(sp_name.removeprefix("SHELL_POSITION_").lower())

    custom_options = {k: _custom_option_value(v) for k, v in proto_plot.custom_options.items()}

    mesh_scoping = proto_plot.mesh_scoping if proto_plot.HasField("mesh_scoping") else None

    return PlotDefinition(
        result_type=result_type,
        location=proto_plot.location,
        name=proto_plot.name or None,
        fields=fields,
        average_by_entity=proto_plot.average_by_entity,
        as_linear=proto_plot.as_linear,
        on_skin=proto_plot.on_skin,
        mesh_scoping=mesh_scoping,
        named_selection_id=proto_plot.named_selection_id or None,
        set_ids=list(proto_plot.set_ids) or None,
        all_sets=proto_plot.all_sets,
        last_set=proto_plot.last_set,
        script=proto_plot.script or None,
        custom_options=custom_options or None,
        include_displacement=proto_plot.include_displacement,
        shell_position=shell_position,
        id=proto_plot.id or None,
        creation_time=getattr(proto_plot, "creation_time", None) or None,
        supports_monitoring=getattr(proto_plot, "supports_monitoring", None),
    )


def _proto_field_to_field(proto_field: models.Field) -> Field:
    try:
        name = ResultFieldName(proto_field.name)
    except ValueError:
        name = proto_field.name  # type: ignore[assignment]

    components = None
    if proto_field.components:
        components = []
        for c in proto_field.components:
            try:
                components.append(Component(c))
            except ValueError:
                components.append(c)  # type: ignore[arg-type]

    return Field(name=name, components=components)


def _custom_option_value(cov: models.CustomOptionsValue) -> int | float | str | bool:
    if cov.WhichOneof("_bool") == "bool":
        return cov.bool
    raw_float = cov.float
    if raw_float != 0.0:
        return raw_float
    if cov.int32 != 0:
        return cov.int32
    return cov.string
