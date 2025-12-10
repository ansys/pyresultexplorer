PyResultExplorer
================

Python interface to Ansys Result Explorer.

.. contribute_start

How to install
--------------

At least two installation modes are provided: user and developer.

For users
^^^^^^^^^

In order to install PyResultExplorer, make sure you
have the latest version of `pip`. To do so, run:

.. code:: bash

    python -m pip install -U pip

Then, you can simply execute:

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

    print("Put sample code here")

For more comprehensive usage information, see the Examples.
