PyResultExplorer
================

Python interface to Ansys Result Explorer.

https://github.com/user-attachments/assets/ca332819-89d5-4c64-8101-1df0b007e05d

**Warning** - **Early Development Stage**
   
PyResultExplorer is currently in the very early stages of development. The interface
is rough and subject to significant changes. Expect rapid and potentially breaking
changes in the coming months as the API evolves and stabilizes.

.. contribute_start

How to install
--------------

At least two installation modes are provided: user and developer.

For users
^^^^^^^^^

To install PyResultExplorer:

.. code:: bash

    python -m pip install git+https://github.com/ansys-internal/pyresultexplorer

For developers
^^^^^^^^^^^^^^

Installing PyResultExplorer in developer mode allows
you to modify the source and enhance it.

#. Start by cloning this repository:

   .. code:: bash

      git clone https://github.com/ansys-internal/pyresultexplorer

#. Create a fresh-clean Python environment and activate it:

   .. code:: bash

      # Create a virtual environment
      uv venv

      # Activate it in a POSIX system
      source .venv/bin/activate

      # Activate it in Windows
      .venv\Scripts\activate

#. Install with latest required build system, doc, and testing dependencies:

   .. code:: bash

      uv sync --all-groups

A note on pre-commit
^^^^^^^^^^^^^^^^^^^^

The style checks take advantage of `pre-commit`. You can install this tool via:

.. code:: bash

    python -m pip install pre-commit
    pre-commit install



Basic usage
^^^^^^^^^^^

This code shows how to import pyresultexplorer and use some basic capabilities:

.. code:: python

    ... coming soon ...

For more comprehensive usage information, see the Examples.
