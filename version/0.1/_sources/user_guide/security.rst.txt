Security
########


This section provides information about security considerations when using PyResultExplorer,
providing guidance for secure usage of the library.


Network security
================

Result Explorer and PyResultExplorer follow a secure-by-default approach.
By default, all communication between the client and the application is encrypted and authenticated.
Some differences exist between the managed local instance and a remote instance, which are described below.

Managed local instance
----------------------

When launching a managed local instance, the :meth:`launch_result_explorer <ansys.result_explorer.core.launch_result_explorer>` function performs these actions:

1. Launches the Result Explorer server as a sub-process on the local machine, using SSL
   (with self-signed certificates generated on the fly, unless otherwise provided)
   and token-based authentication. The token is unique to this instance and owned by the PyResultExplorer process.
2. Opens the frontend in a local web browser (either the system default or through Playwright) to connect to the server,
   registering the frontend instance using a Session ID.
   The Session ID is unique to this frontend instance and owned by the PyResultExplorer process.
3. Creates a :class:`Client <ansys.result_explorer.core.Client>` object that connects to the scripting gateway
   using a secure gRPC channel with TLS encryption and Session ID-based authentication.
   The Session ID acts as a session-scoped bearer credential.
4. Uses the PyResultExplorer client to authenticate the frontend against the server using the auth token.


Connecting to an existing instance
-----------------------------------

When connecting to an existing Result Explorer instance (local or remote), you can grab the connection token from the Result Explorer GUI
and pass it to the :meth:`Client.connect_with_token <ansys.result_explorer.core.Client.connect_with_token>` function.
If the instance was launched with default settings, the connection is secure by default, using TLS encryption and authentication, as described in the preceding section.

.. note:: In case of a remote instance using self-signed certificates, you may need to provide the Certificate Authority (CA) certificate to the client for proper TLS verification.
  You can do this by passing the CA certificate path to the :meth:`Client constructor <ansys.result_explorer.core.Client>` using the ``ca_cert_path`` parameter.


Library and third-party vulnerabilities
=======================================

PyResultExplorer is regularly scanned for security vulnerabilities using automated tools
such as Bandit for code security analysis and Safety for dependency vulnerability checking.
These scans are integrated into the CI pipeline to ensure continuous security monitoring.


Reporting vulnerabilities
==========================

If you discover a security vulnerability in PyResultExplorer, please do not report it
through GitHub issues. Instead, refer to the `SECURITY.md <https://github.com/ansys/pyresultexplorer/blob/main/SECURITY.md>`_
file in the repository for instructions on how to report security issues to the
PyAnsys Core team.