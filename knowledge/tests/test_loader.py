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

"""Tests for loading and searching knowledge artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from ansys.result_explorer.knowledge.loader import load_knowledge_store


def test_load_knowledge_store_and_search(tmp_path: Path) -> None:
    """Load test corpus files and return expected search match."""
    manifest = {
        "schema_version": "1",
        "knowledge_version": "0.1.dev0",
        "core_version": "0.1.dev0",
        "source_commit": "abc",
        "generated_at_utc": "2026-01-01T00:00:00+00:00",
        "corpus_files": {
            "api": "api_index.jsonl",
            "examples": "examples_index.jsonl",
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    api_record = {
        "id": "1",
        "corpus": "api",
        "text": "symbol: Client\nsummary: Main entry point",
        "source_path": "src/ansys/result_explorer/core/client.py",
        "source_sha256": "x",
        "section": "public_symbol",
        "symbol_names": ["Client"],
        "tags": ["api", "public"],
    }
    examples_record = {
        "id": "2",
        "corpus": "examples",
        "text": "workspace = rx.create_workspace(name='Demo')",
        "source_path": "examples/002-workspace-and-views.py",
        "source_sha256": "y",
        "section": "chunk_1",
        "symbol_names": [],
        "tags": ["example", "workspace"],
    }

    (tmp_path / "api_index.jsonl").write_text(json.dumps(api_record) + "\n", encoding="utf-8")
    (tmp_path / "examples_index.jsonl").write_text(
        json.dumps(examples_record) + "\n",
        encoding="utf-8",
    )

    store = load_knowledge_store(tmp_path)
    matches = store.search("create workspace", top_k=3)

    assert len(matches) == 1
    assert matches[0].id == "2"
