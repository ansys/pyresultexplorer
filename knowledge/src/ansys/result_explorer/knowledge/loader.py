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

"""Knowledge loader and simple retrieval utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from .schema import KnowledgeManifest, KnowledgeRecord


@dataclass
class KnowledgeStore:
    """Hold loaded knowledge artifacts and retrieval helpers."""

    manifest: KnowledgeManifest
    records_by_corpus: dict[str, list[KnowledgeRecord]]

    def search(
        self, query: str, *, corpus: str | None = None, top_k: int = 8
    ) -> list[KnowledgeRecord]:
        """Search records by simple token overlap scoring.

        Parameters
        ----------
        query : str
            User query to score against artifact text.
        corpus : str, optional
            Restrict search to one corpus.
        top_k : int, optional
            Maximum number of records to return.

        Returns
        -------
        list[KnowledgeRecord]
            Top ranked matching records.

        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        selected = self.records_by_corpus
        if corpus is not None:
            selected = {corpus: self.records_by_corpus.get(corpus, [])}

        scored: list[tuple[int, KnowledgeRecord]] = []
        for records in selected.values():
            for record in records:
                haystack = " ".join([record.text, record.section, " ".join(record.tags)]).lower()
                score = _token_overlap_score(query_tokens, haystack)
                if score > 0:
                    scored.append((score, record))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [item[1] for item in scored[:top_k]]


def load_knowledge_store(data_dir: str | Path | None = None) -> KnowledgeStore:
    """Load all knowledge artifact files into memory.

    Parameters
    ----------
    data_dir : str | Path, optional
        Override data directory path. If omitted, packaged data is used.

    Returns
    -------
    KnowledgeStore
        Loaded store with manifest and corpora.

    """
    if data_dir is None:
        data_dir = resources.files("ansys.result_explorer.knowledge").joinpath("data")

    data_path = Path(str(data_dir))
    manifest = _read_manifest(data_path / "manifest.json")

    records_by_corpus: dict[str, list[KnowledgeRecord]] = {}
    for corpus, file_name in manifest.corpus_files.items():
        records_by_corpus[corpus] = _read_jsonl_records(data_path / file_name)

    return KnowledgeStore(manifest=manifest, records_by_corpus=records_by_corpus)


def _read_manifest(path: Path) -> KnowledgeManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    return KnowledgeManifest(**data)


def _read_jsonl_records(path: Path) -> list[KnowledgeRecord]:
    records: list[KnowledgeRecord] = []
    if not path.exists():
        return records

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(KnowledgeRecord(**json.loads(stripped)))

    return records


def _tokenize(text: str) -> set[str]:
    return {token for token in text.lower().split() if token}


def _token_overlap_score(query_tokens: set[str], haystack: str) -> int:
    return sum(1 for token in query_tokens if token in haystack)
