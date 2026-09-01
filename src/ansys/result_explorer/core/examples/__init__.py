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

"""Helpers to access example test files used in examples."""

from ansys.result_explorer.core.models import SnapshotSettings

from .test_files import ExampleKeys, get_example_file


# return SnapshotSettings for examples to use consistent settings across screenshots
def get_example_snapshot_settings() -> SnapshotSettings:
    """Get snapshot settings for examples."""
    return SnapshotSettings(
        height=600,
        width=800,
        show_time_stamp=False,
        show_logo=True,
        show_legend=True,
        show_solution_name=False,
        show_result_picker=True,
        transparent_background=False,
        background_color="#FFFFFF",
    )
