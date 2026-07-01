.. _ref_user_guide:

User guide
##########

.. toctree::
   :maxdepth: 2
   :hidden:

   solutions-views
   workspace-viewports
   security

This section walks you through the basics of how to interact with Result Explorer. 
For more elaborate examples, see :doc:`/examples/index`. For more details on the PyResultExplorer API, see :doc:`/api/index`.

The PyResultExplorer library is organized around the following core concepts based on the Result Explorer app structure: 

- **Instance**: Represents a running instance of the Result Explorer app. 
  An instance can manage multiple workspaces and solutions.

- **Client**: The main entry point for interacting with the Result Explorer API. 
  It provides methods to launch or connect to an instance, manage workspaces and solutions, and query results.

- **Solution**: Represents a simulation solution loaded into Result Explorer. 
  You can interact with the solution to access its metadata, create views, and visualize results.

- **View**: A displayable item under a solution. Views can include mesh views, plots, charts, logs, convergence and contact tracker charts.
  You can create multiple views for a solution and customize their settings.

- **Workspace**: A collection of viewports, their layout, and associated workspace settings.
  Solution and views are shared across workspaces.
  You can have multiple workspaces in an instance.

- **Viewport**: A display area used to show a view.
  You can have multiple viewports in a workspace, each showing possibly different views of the solution data.
  A view can be displayed in multiple viewports, and each viewport can have its own display options.