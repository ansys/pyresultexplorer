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

"""Helpers to get the path to test files used in examples."""

import pathlib
from enum import Enum, auto


def get_root_repo_path() -> pathlib.Path:
    """Get the root path of the repository."""
    return pathlib.Path(__file__).parent.parent.parent.parent.parent.parent


def get_test_data_folder() -> pathlib.Path:
    """Get the path to the test data folder."""
    try:
        return get_root_repo_path() / "tests" / "data"
    except NameError:
        # Sphinx-gallery execution context where __file__ is not defined
        return pathlib.Path.cwd() / ".." / "tests" / "data"


class ExampleKeys(Enum):
    """Keys for the example test files."""

    RST_MULTIPLE_CONNECTIONS = auto()
    RST_CP_TRANSIENT = auto()


EXAMPLE_FILES = {
    ExampleKeys.RST_MULTIPLE_CONNECTIONS: "multiple_connections.rst",
    ExampleKeys.RST_CP_TRANSIENT: "cp_trans/file.rst",
}


def get_example_file(example_key: ExampleKeys) -> pathlib.Path:
    """Get the path to an example test file based on the provided key."""
    return get_test_data_folder() / EXAMPLE_FILES[example_key]
