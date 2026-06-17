Getting started
===============

This section will help you get started with PyResultExplorer, from installation to controlling your first Result Explorer session.


Installation
------------

To use PyResultExplorer, a licensed copy of Ansys Result Explorer is required.
Please contact your Ansys representative to obtain a license of the product.

Install Result Explorer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install Result Explorer, download the installer from the Ansys Customer Portal and
follow the installation instructions provided in the Result Explorer User's Guide on the Ansys Help.

You can install either the Desktop or Server version of Result Explorer. 
Both versions are compatible with PyResultExplorer.

Configure the installation path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After installing Result Explorer, you must register its installation path as an environment variable 
so that PyResultExplorer can locate it.
Set one of the following environment variables depending on your installation:

- ``ANSYS_RESULT_EXPLORER_SERVER``: points directly to the server installation directory (the directory containing the ``viz-server`` executable)
- ``ANSYS_RESULT_EXPLORER_DESKTOP``: points to the desktop application root directory (the directory containing the ``result-explorer-desktop`` executable)


Install the package
^^^^^^^^^^^^^^^^^^^^

The latest ``ansys.result_explorer.core`` package supports Python 3.11 through Python 3.14 on Windows, Linux, and Mac OS.
You should consider installing PyResultExplorer in a virtual environment.

Until the project is open sourced, you can install ``pyresultexplorer`` directly from sources:

.. code:: bash

    python -m pip install git+https://github.com/ansys-internal/pyresultexplorer


Launch or connect to Result Explorer
------------------------------------

PyResultExplorer provides two ways to work with Result Explorer, either by launching a new instance or connecting to an existing one.
Choose the option that best fits your workflow.

Connect to an existing instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If Result Explorer is already running (desktop app or remote server), grab the **Connection Token** 
from the Result Explorer GUI and use it:

.. code:: python

    from ansys.result_explorer.core import Client

    # Get the connection token from the Result Explorer GUI
    rx = Client.connect_with_token("your-connection-token-from-gui")

    # Now use the client to interact with Result Explorer
    solutions = rx.list_solutions()

The token is a base64-encoded string that contains all connection details (host, port, session ID, etc.). 
This approach is ideal for connecting to remote servers or existing desktop instances.


Launch a new instance
^^^^^^^^^^^^^^^^^^^^^

Use ``launch_result_explorer()`` to start a fresh Result Explorer session, with the GUI served in a browser window. 
You have the option to customize the server and web configurations:

.. code:: python

    from ansys.result_explorer.core import launch_result_explorer, ServerLaunchConfig, WebLaunchConfig, BrowserType

    # Simplest: launch with defaults
    rx = launch_result_explorer()

    # Or with custom configuration
    server_config = ServerLaunchConfig(port=5100, num_threads=12)
    web_config = WebLaunchConfig(browser_type=BrowserType.SYSTEM_DEFAULT)
    rx = launch_result_explorer(server_config, web_config)

The Result Explorer web UI can run in three modes:

- ``BrowserType.SYSTEM_DEFAULT`` — Opens the system's default browser
- ``BrowserType.PLAYWRIGHT_CHROMIUM`` — Uses Chromium via Playwright, with visible window
- ``BrowserType.PLAYWRIGHT_CHROMIUM_HEADLESS`` — Uses Chromium via Playwright in headless mode (default)

The instance lifecycle is tied to the client. When you destroy the client, the server automatically stops.


Compatibility with Result Explorer versions
-------------------------------------------

The current version of PyResultExplorer is compatible with Ansys Result Explorer 2026.7.0.


Report issues
-------------

Use the `PyResultExplorer Issues <https://github.com/ansys-internal/pyresultexplorer/issues>`_
page to report bugs and request new features. When possible, use the issue
templates provided. If your issue does not fit into one of these templates,
click the link for opening a blank issue.

On the `PyResultExplorer Discussions <https://github.com/ansys-internal/pyresultexplorer/discussions>`_ page
or the `Discussions <https://discuss.ansys.com/>`_ page on the Ansys Developer portal,
you can post questions, share ideas, and get community feedback.

To reach the project support team, email `pyansys.core@ansys.com <pyansys.core@ansys.com>`_.