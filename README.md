# PyResultExplorer

[![PyAnsys](https://img.shields.io/badge/Py-Ansys-ffc107.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABDklEQVQ4jWNgoDfg5+OQgMJ/0AqCqXGQMEBAwBEKQj5gGDjQsA80UeCDscxrD4YhGsgABEELnC5zAwAu6ACKQDAQzNBFwAAVdgFEAnfDiQAATyIBaAFgCbkAI5DQwAVGAYkAMA4gHgg2AC+AAgQIABggagAqyAD4AACkR7cEdcEBQOPjIvAEtRDoAbYLANQAZGsBEAFeBwCsAY0HgGCAAEQTaDj7xQABItJ+S3DsQAAAABJRU5ErkJggg==)](https://docs.pyansys.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Apache](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)


PyResultExplorer is a Python client library for Ansys Result Explorer, which is a tool to explore and visualize structural simulation results.
With PyResultExplorer you can:
- Launch a new or connect to an existing Result Explorer session
- Automate and customize your Result Explorer post-processing workflows


## Installation

### For users

To install PyResultExplorer (temporarily, until it's not open-sourced):

```bash
python -m pip install git+https://github.com/ansys/pyresultexplorer
```

### For developers

Installing PyResultExplorer in developer mode allows you to modify the source and enhance it.

Start by cloning this repository:

```bash
git clone https://github.com/ansys/pyresultexplorer
```

Create a fresh-clean Python environment and activate it:

```bash
# Create a virtual environment
uv venv

# Activate it in a POSIX system
source .venv/bin/activate

# Activate it in Windows
.venv\Scripts\activate
```

Install with latest required build system, doc, and testing dependencies:

```bash
uv sync --all-groups
```

The style checks take advantage of `pre-commit`. You can install it with `pre-commit install`.


## Basic usage

The following code snippet shows how to launch a new Result Explorer instance,
create a solution and load a displacement view.

```python
import os
from ansys.result_explorer.core import launch_result_explorer

# Launch a new Result Explorer session
rx = launch_result_explorer()

# Create a solution from an APDL RST file
sol = rx.create_solution(
    name="PyRX Solution",
    file_path=os.path.join("tests", "data", "multiple_connections.rst"),
)

# Create a new workspace and load a displacement view
workspace = rx.create_workspace(name="PyRX Workspace")

views = sol.views
print("Views in solution:")
for v in views:
    print(f" - {v}")

view = next((v for v in views if "Displacement" in v.name), None)
viewport = workspace.assign_view(view=view, wait=True)

# Take a screenshot of the view and save to disk
snapshot_data = viewport.take_snapshot()

print("Saving snapshot to file...")
with open(view.name + ".png", "wb") as image_file:
    image_file.write(snapshot_data)
```

## License

This project is licensed under the Apache 2.0 license agreement. See the [LICENSE](./LICENSE) file for details.

## Resources

- [PyResultExplorer documentation](https://fuzzy-adventure-gzkzk5l.pages.github.io/)
- [Repository's Issues page](https://github.com/ansys/pyresultexplorer/issues)
- [Repository's Discussions page](https://github.com/ansys/pyresultexplorer/discussions)

For general PyAnsys questions, email [pyansys-core@synopsys.com](mailto:pyansys-core@synopsys.com).