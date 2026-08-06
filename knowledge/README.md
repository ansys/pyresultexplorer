# ansys-result-explorer-knowledge

This package provides versioned knowledge artifacts for `ansys-result-explorer-core`.

It is generated from source content in the PyResultExplorer repository:

- Public API surface in `src/ansys/result_explorer/core`
- Runnable examples in `examples/`
- Documentation pages in `doc/source/user_guide` and `doc/source/api`

The package is intended to be consumed by MCP servers and other automation
systems that need deterministic, local context without runtime downloads.

## Goals

- Strict version coupling with `ansys-result-explorer-core`
- Deterministic generated artifacts
- Source provenance in every record

## Generate artifacts

Generated artifact files are not committed to this repository. They are generated
in CI and included in the published wheel.

Run from this package directory:

```bash
pyrx-knowledge-generate --repo-root .. --output-dir src/ansys/result_explorer/knowledge/data
```

## Artifact files

- `manifest.json`
- `api_index.jsonl`
- `examples_index.jsonl`
- `guide_index.jsonl`
