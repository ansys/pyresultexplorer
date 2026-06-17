Contribute
---------------

Installing PyResultExplorer in developer mode allows
you to modify the source and enhance it.

Before contributing to the project, please refer to the `PyAnsys Developer's guide`_ and then follow these steps:

#. Start by cloning this repository:

   .. code:: bash

      git clone https://github.com/ansys-internal/pyresultexplorer

#. Create a fresh-clean Python environment and activate it:

   .. code:: bash

      # Create a virtual environment
      uv venv

      # Activate it in a POSIX system
      source .venv/bin/activate

      # Activate it in Windows CMD environment
      .venv\Scripts\activate.bat

      # Activate it in Windows Powershell
      .venv\Scripts\Activate.ps1

#. Install the project:

    .. code:: bash

      uv sync --all-groups

How to test
-----------

Coming soon.


A note on pre-commit
^^^^^^^^^^^^^^^^^^^^

The style checks take advantage of `pre-commit`_. Developers are not forced but
encouraged to install this tool via:

.. code:: bash

    python -m pip install pre-commit && pre-commit install


Documentation
-------------

For building documentation, you can either run the usual rules provided in the
`Sphinx`_ Makefile, such as:

.. code:: bash

    make -C doc/ html && open doc/html/index.html

You can also build a live version of the documentation that you can preview in the browser,
with automatic reload on change:

.. code:: bash

    sphinx-autobuild source build


Distributing
------------

If you would like to create either source or wheel files, start by installing
the building requirements and then executing the build module:

.. code:: bash

    python -m pip install -r requirements/requirements_build.txt
    python -m build
    python -m twine check dist/*


.. LINKS AND REFERENCES
.. _pip: https://pypi.org/project/pip/
.. _pre-commit: https://pre-commit.com/
.. _PyAnsys Developer's guide: https://dev.docs.pyansys.com/
.. _pytest: https://docs.pytest.org/en/stable/
.. _Sphinx: https://www.sphinx-doc.org/en/master/