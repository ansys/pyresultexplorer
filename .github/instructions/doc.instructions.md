---
applyTo: "doc/source/**/*.rst"
---

# Documentation Style and Tools

## Overview

This document outlines standards for building and maintaining project documentation, following the [PyAnsys Development Guide](https://github.com/ansys/pyansys-dev-guide/tree/main/doc/source/doc-style).

Good documentation provides:
- Increased adoption and improved developer experience
- Faster onboarding of contributors and users
- Better code maintenance
- Clearer understanding of project features

For **docstring guidelines**, see [../copilot-instructions.md](../copilot-instructions.md#docstring-guidelines).

## General Writing Guidelines

Follow the [Google Developer Documentation Style Guide](https://developers.google.com/style/):

- **Sentence case** for headings and titles
- **Active voice** (prefer "the function returns" over "it is returned")
- **Present tense** (prefer "returns" over "will return")
- **Short, clear sentences** (easier to read and translate)

## Documentation Structure

A complete PyAnsys library documentation should contain:

- Module, function, class, and method docstrings
- A full gallery of examples
- General content on installing, using, and contributing
- Link to documentation from the repository's README file

## Sphinx Configuration

### Required Configuration Files

Documentation builds use:
- **`conf.py`** — Sphinx configuration
- **`Makefile`** (POSIX) or **`make.bat`** (Windows) — Build automation

### Key Sphinx Options

When building documentation, include these options:

- `-j auto` — Auto-detect number of CPU cores for parallel builds
- `-W` — Turn warnings into errors (maximizes documentation health)
- `--keep-going` — Continue building despite warnings (shows full warning set)

## Documentation Style Tools

### Numpydoc Validation

Validates docstring structure for Numpydoc-compliant docstrings.

**Configuration in `conf.py`:**
```python
extensions = ["numpydoc", ...]
numpydoc_validation_checks = {"GL08"}  # Example: require all docstrings
```

For available checks, see [numpydoc validation documentation](https://numpydoc.readthedocs.io/en/latest/validation.html#built-in-validation-checks).

### Docformatter

Automatically formats Python docstrings per [PEP 257](https://peps.python.org/pep-0257/).

**Installation:**
```bash
pip install docformatter
```

**Usage:**
```bash
docformatter -r -i --wrap-summaries 70 --wrap-descriptions 70 src/
```

### Doctest

Python standard library module for checking docstring examples.

**Configuration in `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
addopts = "--doctest-modules"
```

**Usage:**
```bash
pytest --doctest-modules
```

### Interrogate

Checks docstring coverage (similar to code coverage).

**Installation:**
```bash
pip install interrogate
```

**Configuration in `pyproject.toml`:**
```toml
[tool.interrogate]
exclude = ["setup.py", "doc", "tests"]
color = true
verbose = 2
```

**Usage:**
```bash
interrogate -vv src/
```

### Blacken-docs

Formats code blocks in RST/Markdown documentation files.

**Installation:**
```bash
pip install blacken-docs
```

**Usage:**
```bash
blacken-docs -l 88 doc/**/*.rst
```

### Codespell

Checks for common spelling mistakes in text files.

**Installation:**
```bash
pip install codespell
```

**Usage:**
```bash
codespell --write-changes --ignore-words=<FILE>
```

### Pydocstyle

Checks docstring compliance with [PEP 257](https://peps.python.org/pep-0257/).

**Installation:**
```bash
pip install pydocstyle
```

**Configuration in `pyproject.toml`:**
```toml
[tool.pydocstyle]
convention = "numpy"
```

**Usage:**
```bash
pydocstyle src/
```

### Vale

Linting tool for documentation prose. Applies the [Google Developer Documentation Style Guide](https://developers.google.com/style/) plus custom Ansys rules.

**Installation:**
```bash
brew install vale  # macOS
# or download from https://github.com/errata-ai/vale/releases
```

**Configuration:** `.vale.ini` in the `doc/` folder

**Usage:**
```bash
vale sync                          # Download Vale packages
vale .                             # Check all files
vale doc/                          # Check specific folder
vale --config=doc/.vale.ini .      # Use custom config
```

**Address issues:**
- Edit files to fix issues
- Or add terms to `doc/styles/config/vocabularies/ANSYS/accept.txt`

## Building Documentation

### From the `doc/` directory

**POSIX systems (Makefile):**
```bash
make html      # Build HTML documentation
make pdf       # Build PDF documentation
make clean     # Clean build artifacts
```

**Windows (make.bat):**
```bash
make.bat html  # Build HTML documentation
make.bat pdf   # Build PDF documentation
make.bat clean # Clean build artifacts
```

### Common Sphinx Build Options

```bash
sphinx-build -j auto -W --keep-going source build/html
```

## Documentation Hosting

Documentation should be public and hosted using GitHub Pages:

- **Option 1:** `gh-pages` branch in the library repository
- **Option 2:** `gh-pages` branch in separate `<library-repository>-docs` repository

For DNS configuration, refer to the [PyAnsys Development Guide](https://github.com/ansys/pyansys-dev-guide/tree/main/doc/source/doc-style).

## References

- [Numpydoc Manual - Style Guide](https://numpydoc.readthedocs.io/en/latest/format.html)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Developer Documentation Style Guide](https://developers.google.com/style/)
- [PyAnsys Development Guide - Doc Style](https://github.com/ansys/pyansys-dev-guide/tree/main/doc/source/doc-style)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Quick Reference](https://docutils.sourceforge.io/docs/user/rst/quickref.html)
