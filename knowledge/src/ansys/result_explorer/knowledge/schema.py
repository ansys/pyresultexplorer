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

"""Schema definitions for knowledge artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KnowledgeRecord:
    """Represent one searchable knowledge record."""

    id: str
    corpus: str
    text: str
    source_path: str
    source_sha256: str
    section: str
    symbol_names: list[str]
    tags: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert the record to a plain dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeManifest:
    """Describe the generated knowledge artifact set."""

    schema_version: str
    knowledge_version: str
    core_version: str
    source_commit: str
    generated_at_utc: str
    corpus_files: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        """Convert the manifest to a plain dictionary."""
        return asdict(self)
