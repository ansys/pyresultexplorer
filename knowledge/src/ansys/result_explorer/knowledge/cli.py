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

"""Command-line interface for knowledge artifact generation."""

from __future__ import annotations

import argparse

from .generator import generate_knowledge_artifacts


def main() -> None:
    """Generate knowledge artifacts from repository sources."""
    parser = argparse.ArgumentParser(description="Generate PyResultExplorer knowledge artifacts")
    parser.add_argument(
        "--repo-root", required=True, help="Path to the pyresultexplorer repository root"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where generated knowledge files are written",
    )
    args = parser.parse_args()

    generate_knowledge_artifacts(repo_root=args.repo_root, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
