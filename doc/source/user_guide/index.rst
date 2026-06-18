.. _ref_user_guide:

==========
User guide
==========

.. toctree::
   :maxdepth: 2
   :hidden:

   solutions-views
   workspace-viewports
   security

This section walks you through the basics of how to interact with Result Explorer. 
For more elaborate examples, see :doc:`/examples/index`. For more details on the PyResultExplorer API, see :doc:`/api/index`.

The PyResultExplorer library is organized around the following core concepts based on the Result Explorer application structure: 

- **Instance**: Represents a running instance of the Result Explorer application. 
  An instance can manage multiple workspaces and solutions.

- **Client**: The main entry point for interacting with the Result ExplorerAPI. 
  It provides methods to launch or connect to an instance, manage workspaces and solutions, and query results.

- **Solution**: Represents a simulation solution loaded into Result Explorer. 
  You can interact with the solution to access its metadata, create views, and visualize results.

- **View**: Represents a specific view of the solution data, such as a plot or a chart. 
  You can create multiple views for a solution and customize their settings.

- **Workspace**: A viewport layout and workspace-specific state.
  Solution and views are shared across workspaces.
  You can have multiple workspaces in an instance.

- **Viewport**: A specific area within a workspace where a view is displayed. 
  You can have multiple viewports in a workspace, each showing different views of the solution data.
  A view can be displayed in multiple viewports, and each viewport can have its own display options.