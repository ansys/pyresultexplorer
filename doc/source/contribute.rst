Contribute
==========

Overall guidance on contributing to a PyAnsys library appears in the
`Contributing <https://dev.docs.pyansys.com/how-to/contributing.html>`_ topic
in the *PyAnsys Developer's Guide*. Ensure that you are thoroughly familiar
with this guide before attempting to contribute to PyResultExplorer.

The following contribution information is specific to PyResultExplorer.

Install in developer mode
-------------------------

Installing PyResultExplorer in developer mode allows you to modify the source and enhance it.

#. Start by cloning this repository:

   .. code:: bash

      git clone https://github.com/ansys-internal/pyresultexplorer

#. Create a fresh-clean Python environment and activate it, we recommend using `uv <https://pypi.org/project/uv/>`_ for this purpose:

   .. code:: bash

      # Create a virtual environment
      uv venv

      # Activate it in a POSIX system
      source .venv/bin/activate

      # Activate it in Windows CMD environment
      .venv\Scripts\activate.bat

      # Activate it in Windows Powershell
      .venv\Scripts\Activate.ps1

#. Install the library with its dependencies:

   .. code:: bash

      uv sync --all-groups

#. Install pre-commit hooks to automatically check code style before committing:

   .. code:: bash

      pre-commit install

How to test
-----------

To run the tests, you must have Result Explorer installed on your machine.
Navigate to the root directory of the repository and run ``pytest``.
You can specify additional options to control the test execution, for example:

.. code:: bash

    # Full test suite, running against a native instance of Result Explorer
    pytest tests --launch-native

    # Filter by file, additional verbosity, and show print statements
    pytest -vv -s tests\test_launcher.py --launch-native

    # Show browser window for visual feedback
    pytest tests --launch-native --headed

    # To run against an already running instance
    pytest tests --connection-token=<token>  

.. tip::

   To interactively debug tests in Visual Studio Code, you may need
   to disable the ``install_browser`` fixture, as it may interfere with the debugger. 

Documentation
-------------

To build the documentation locally, navigate to the ``docs`` directory and run this command:

.. code:: bash

    # On Linux or macOS
    make html
    
    # On Windows
    ./make.bat html

You can set the environment variable ``PYRX_DOC_SKIP_GALLERY`` to ``1`` to skip building the gallery examples,
which can take a long time to build. 

Note that to build the documentation examples you must have Result Explorer
installed on your machine.
