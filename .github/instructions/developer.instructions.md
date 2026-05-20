# Result Explorer Development Instructions

## Architecture Overview

### Result Explorer

Result Explorer is a tool to explore and visualize structural simulation results. It enables you to:
- Interactively explore your results
- Compare results of different models side-by-side
- Monitor running simulations in real-time
- Explore locally stored results or connect to remote compute resources (eliminating the need to transfer large result files to your local machine)

**Available as:** Desktop application and web application

#### Client-Server Architecture

Result Explorer uses a flexible client-server architecture where:
- **Server** is responsible for reading and processing simulation results and exposes HTTP(S) APIs (REST and WebSocket)
- **Gateway** is a scripting proxy that runs alongside the server with HTTP(S) and gRPC APIs, routing gRPC messages to the web UI over WebSocket
- **Web UI** is a client that connects to both the server (HTTP/REST) and gateway (WebSocket) for visualization and scripting
- **PyResultExplorer** is a Python client that communicates with the gateway's gRPC API, effectively acting as a client of the web UI scripting interface

**Communication:**
```
Server (HTTP/REST/WS) ← → Web UI
Gateway (HTTP(S)/gRPC) ← → Web UI (WebSocket)
PyResultExplorer ← → Gateway (gRPC)
```

**Deployment flexibility:**
- **Desktop:** Server, gateway, and web UI run on the same machine packaged together using Electron, creating a standalone desktop application that combines all components
- **Remote:** Web UI runs in a web browser on any device; server and gateway run on a remote machine
- **Collaborative:** Multiple web UIs/clients can connect to the same server and gateway for sharing results
- **Multi-source:** Multiple servers can be accessed through different gateways

#### Key Concepts

**Result Provider:** A Result Explorer server that provides simulation results to clients. Identified by a URL, it can run on a local machine, remote server, or HPC cluster. Multiple providers can be registered with a client.

**Solution:** A container for result data associated with a result file. Creating a solution is lightweight and doesn't require reading the full result data—only metadata is loaded initially. Actual data loads on-demand when visualizing specific results. Multiple solutions can be loaded simultaneously.

### PyResultExplorer Architecture
PyResultExplorer is a Python client library for Result Explorer that communicates with the gateway's gRPC API. It provides three core layers:

1. **Core Client** (`client.py`)
   - gRPC communication with the gateway's scripting interface
   - Connection management and session handling
   - Entry point for all scripting operations

2. **Object Model** (`objects/`)
   - `Workspace` - Container for solutions and viewports
   - `Solution` - Result data with views and analysis metadata
   - `Viewport` - 3D rendering surface for visualization
   - `CameraPosition` - View control and positioning
   - All objects are proxies to API-side entities (accessed via gateway)

3. **Launch Utilities** (`launch.py`)
   - Server and gateway process management and lifecycle
   - Port auto-discovery and configuration
   - Web UI browser integration (default, Playwright windowed, Playwright headless)
   - Automatic connection verification

## Coding Rules

### API Usage
- **Do not invent APIs** — Only use methods and properties that exist in the codebase. Verify actual method names (e.g., `list_result_providers()` not `result_providers`). When uncertain, check existing code or ask before implementing.
- **Type hints are mandatory** — Add type annotations to all function parameters and return types for clarity and IDE support.

### Code Quality
- **Avoid unnecessarily verbose docstrings** — Docstrings should add value. Omit them if the function name and type hints are self-explanatory. Use docstrings to clarify intent, parameters, and return values when not obvious.
- **Avoid long functions** — Extract helper functions and keep functions focused on a single responsibility. Maximum ~50 lines unless there's a strong reason.
- **Use existing patterns** — Follow established patterns in the codebase (e.g., `@dataclass` for configuration, properties for instance state, context managers for lifecycle).

### Code Style
- **Use ruff check and format** — Run linting and formatting as configured in the repo:
  ```bash
  ruff check src/
  ruff format src/
  ```
- **Fix all linting errors** — Before committing, ensure no errors from `ruff check`.
- **Keep line length ≤100 characters** — Break long lines at logical boundaries.

