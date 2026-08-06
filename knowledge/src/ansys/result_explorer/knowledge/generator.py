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

"""Build deterministic knowledge artifacts from repository content."""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from .schema import KnowledgeManifest, KnowledgeRecord

SCHEMA_VERSION = "1"
API_CORPUS = "api"
EXAMPLES_CORPUS = "examples"
GUIDE_CORPUS = "guide"


def generate_knowledge_artifacts(repo_root: str | Path, output_dir: str | Path) -> None:
    """Generate and write all knowledge artifacts.

    Parameters
    ----------
    repo_root : str | Path
        Root of the pyresultexplorer repository.
    output_dir : str | Path
        Output directory for generated artifact files.

    """
    repo = Path(repo_root).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    knowledge_version = _read_project_version(repo / "knowledge" / "pyproject.toml")
    core_version = _read_project_version(repo / "pyproject.toml")
    _validate_version_coupling(knowledge_version=knowledge_version, core_version=core_version)
    source_commit = _read_git_commit(repo)

    api_records = sorted(_build_api_records(), key=lambda rec: rec.id)
    example_records = sorted(_build_example_records(repo), key=lambda rec: rec.id)
    guide_records = sorted(_build_guide_records(repo), key=lambda rec: rec.id)

    corpus_files = {
        API_CORPUS: "api_index.jsonl",
        EXAMPLES_CORPUS: "examples_index.jsonl",
        GUIDE_CORPUS: "guide_index.jsonl",
    }

    _write_jsonl(out / corpus_files[API_CORPUS], api_records)
    _write_jsonl(out / corpus_files[EXAMPLES_CORPUS], example_records)
    _write_jsonl(out / corpus_files[GUIDE_CORPUS], guide_records)

    manifest = KnowledgeManifest(
        schema_version=SCHEMA_VERSION,
        knowledge_version=knowledge_version,
        core_version=core_version,
        source_commit=source_commit,
        generated_at_utc=datetime.now(tz=timezone.utc).isoformat(),
        corpus_files=corpus_files,
    )
    (out / "manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")


def _build_api_records() -> list[KnowledgeRecord]:
    core = importlib.import_module("ansys.result_explorer.core")
    records: list[KnowledgeRecord] = []

    for name in sorted(core.__dict__):
        if name.startswith("_"):
            continue

        member = core.__dict__[name]
        if inspect.ismodule(member):
            continue

        module_name = getattr(member, "__module__", "")
        if module_name and not module_name.startswith("ansys.result_explorer.core"):
            continue

        signature = _safe_signature(member)
        doc_summary = _doc_summary(member)
        section = "public_symbol"

        text_parts = [f"symbol: {name}"]
        if signature:
            text_parts.append(f"signature: {signature}")
        if doc_summary:
            text_parts.append(f"summary: {doc_summary}")

        text = "\n".join(text_parts)
        records.append(
            _record(
                corpus=API_CORPUS,
                text=text,
                source_path=f"ansys.result_explorer.core::{name}",
                section=section,
                symbol_names=[name],
                tags=["api", "public"],
            )
        )

    return records


def _build_example_records(repo_root: Path) -> list[KnowledgeRecord]:
    examples_dir = repo_root / "examples"
    paths = sorted(path for path in examples_dir.glob("*.py") if path.name[:3].isdigit())

    records: list[KnowledgeRecord] = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for idx, chunk in enumerate(_split_example_chunks(content), start=1):
            if not chunk.strip():
                continue
            section = f"chunk_{idx}"
            records.append(
                _record(
                    corpus=EXAMPLES_CORPUS,
                    text=chunk.strip(),
                    source_path=path.relative_to(repo_root).as_posix(),
                    section=section,
                    symbol_names=[],
                    tags=_derive_tags(chunk, path.name),
                )
            )

    return records


def _build_guide_records(repo_root: Path) -> list[KnowledgeRecord]:
    doc_paths: list[Path] = []
    for base in (repo_root / "doc" / "source" / "user_guide", repo_root / "doc" / "source" / "api"):
        doc_paths.extend(sorted(base.rglob("*.rst")))

    records: list[KnowledgeRecord] = []
    for path in doc_paths:
        content = path.read_text(encoding="utf-8")
        for section, text in _split_rst_sections(content):
            if len(text.strip()) < 20:
                continue
            records.append(
                _record(
                    corpus=GUIDE_CORPUS,
                    text=text.strip(),
                    source_path=path.relative_to(repo_root).as_posix(),
                    section=section,
                    symbol_names=[],
                    tags=["doc", "guide"],
                )
            )

    return records


def _split_example_chunks(content: str) -> list[str]:
    parts = content.split("# %%")
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned if cleaned else [content]


def _split_rst_sections(content: str) -> Iterable[tuple[str, str]]:
    lines = content.splitlines()
    sections: list[tuple[str, list[str]]] = [("root", [])]

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if idx + 1 < len(lines) and _is_heading_underline(lines[idx + 1]):
            title = line.strip() or "untitled"
            sections.append((title, []))
            idx += 2
            continue

        current_title, current_lines = sections[-1]
        current_lines.append(line)
        sections[-1] = (current_title, current_lines)
        idx += 1

    for title, section_lines in sections:
        text = "\n".join(_filter_rst_noise(section_lines)).strip()
        if text:
            yield title, text


def _filter_rst_noise(lines: list[str]) -> list[str]:
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(".. toctree::"):
            continue
        if stripped.startswith(":"):
            continue
        if stripped.startswith(".. _"):
            continue
        kept.append(line)
    return kept


def _is_heading_underline(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return len(set(stripped)) == 1 and stripped[0] in "=#-*^~\"'`"


def _safe_signature(member: object) -> str:
    try:
        return str(inspect.signature(member))
    except (TypeError, ValueError):
        return ""


def _doc_summary(member: object) -> str:
    doc = inspect.getdoc(member)
    if not doc:
        return ""
    return doc.splitlines()[0].strip()


def _derive_tags(content: str, file_name: str) -> list[str]:
    lowered = content.lower()
    tags = ["example", file_name.replace(".py", "")]
    for token in ["workspace", "solution", "view", "viewport", "plot", "chart", "camera"]:
        if token in lowered:
            tags.append(token)
    return sorted(set(tags))


def _record(
    *,
    corpus: str,
    text: str,
    source_path: str,
    section: str,
    symbol_names: list[str],
    tags: list[str],
) -> KnowledgeRecord:
    source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rid = hashlib.sha256(f"{corpus}|{source_path}|{section}|{source_sha256}".encode()).hexdigest()
    return KnowledgeRecord(
        id=rid,
        corpus=corpus,
        text=text,
        source_path=source_path,
        source_sha256=source_sha256,
        section=section,
        symbol_names=symbol_names,
        tags=sorted(set(tags)),
    )


def _write_jsonl(path: Path, records: list[KnowledgeRecord]) -> None:
    lines = [json.dumps(record.to_dict(), sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_project_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as stream:
        data = tomllib.load(stream)
    return str(data["project"]["version"])


def _validate_version_coupling(*, knowledge_version: str, core_version: str) -> None:
    """Validate strict version coupling between knowledge and core packages."""
    if knowledge_version != core_version:
        raise ValueError(
            "Knowledge package version must match core package version exactly. "
            f"knowledge={knowledge_version!r}, core={core_version!r}."
        )


def _read_git_commit(repo_root: Path) -> str:
    head_path = repo_root / ".git" / "HEAD"
    if not head_path.exists():
        return "unknown"

    head = head_path.read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        return head

    ref = head.split(" ", maxsplit=1)[1].strip()
    ref_path = repo_root / ".git" / ref
    if ref_path.exists():
        return ref_path.read_text(encoding="utf-8").strip()

    packed_refs = repo_root / ".git" / "packed-refs"
    if packed_refs.exists():
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            if line.endswith(ref):
                return line.split(" ", maxsplit=1)[0]

    return "unknown"
