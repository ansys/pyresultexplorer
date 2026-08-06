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

"""Tests for knowledge artifact generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ansys.result_explorer.knowledge import generator
from ansys.result_explorer.knowledge.schema import KnowledgeRecord


def test_generate_knowledge_artifacts_writes_manifest_and_corpora(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Write expected corpus files and a manifest with version metadata."""
    repo_root = tmp_path / "repo"
    (repo_root / "knowledge").mkdir(parents=True)

    root_pyproject = """
[project]
version = "0.1.dev0"
""".strip()
    (repo_root / "pyproject.toml").write_text(root_pyproject + "\n", encoding="utf-8")
    (repo_root / "knowledge" / "pyproject.toml").write_text(root_pyproject + "\n", encoding="utf-8")

    output_dir = tmp_path / "out"

    monkeypatch.setattr(generator, "_read_git_commit", lambda _repo: "deadbeef")
    monkeypatch.setattr(
        generator,
        "_build_api_records",
        lambda: [
            KnowledgeRecord(
                id="a",
                corpus="api",
                text="api text",
                source_path="api",
                source_sha256="1",
                section="s",
                symbol_names=["Client"],
                tags=["api"],
            )
        ],
    )
    monkeypatch.setattr(
        generator,
        "_build_example_records",
        lambda _repo: [
            KnowledgeRecord(
                id="b",
                corpus="examples",
                text="example text",
                source_path="examples",
                source_sha256="2",
                section="chunk_1",
                symbol_names=[],
                tags=["example"],
            )
        ],
    )
    monkeypatch.setattr(
        generator,
        "_build_guide_records",
        lambda _repo: [
            KnowledgeRecord(
                id="c",
                corpus="guide",
                text="guide text",
                source_path="doc",
                source_sha256="3",
                section="intro",
                symbol_names=[],
                tags=["doc"],
            )
        ],
    )

    generator.generate_knowledge_artifacts(repo_root=repo_root, output_dir=output_dir)

    assert (output_dir / "api_index.jsonl").exists()
    assert (output_dir / "examples_index.jsonl").exists()
    assert (output_dir / "guide_index.jsonl").exists()

    manifest_data = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["core_version"] == "0.1.dev0"
    assert manifest_data["knowledge_version"] == "0.1.dev0"
    assert manifest_data["source_commit"] == "deadbeef"
    assert set(manifest_data["corpus_files"]) == {"api", "examples", "guide"}


def test_generate_knowledge_artifacts_fails_on_version_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Reject artifact generation when knowledge and core versions differ."""
    repo_root = tmp_path / "repo"
    (repo_root / "knowledge").mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text(
        '[project]\nversion = "0.1.dev0"\n',
        encoding="utf-8",
    )
    (repo_root / "knowledge" / "pyproject.toml").write_text(
        '[project]\nversion = "0.2.dev0"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(generator, "_read_git_commit", lambda _repo: "deadbeef")

    with pytest.raises(ValueError, match="must match core package version exactly"):
        generator.generate_knowledge_artifacts(repo_root=repo_root, output_dir=tmp_path / "out")
