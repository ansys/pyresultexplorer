"""Fixtures for testing Ansys Result Explorer.

To run the tests using a headed browser, append the `--headed` flag
to the pytest command, e.g.:

    pytest -vv --headed tests

"""

import io
import logging
import os
import subprocess
import sys
import uuid
import warnings
from collections.abc import Generator
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import BrowserContext, expect
from syrupy.extensions.image import PNGImageSnapshotExtension

from ansys.result_explorer.core import (
    Client,
    ServerLaunchConfig,
    Solution,
)
from ansys.result_explorer.core.launch import ResultExplorerServerProcess
from ansys.result_explorer.core.models import SnapshotSettings

log = logging.getLogger(__name__)

# Suppress PIL debug output during image comparison
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)


class ToleranceImageSnapshotExtension(PNGImageSnapshotExtension):
    """PNG snapshot extension with pixel-level comparison tolerance.

    Compares images pixel-by-pixel and allows a threshold percentage of
    differing pixels before failing the assertion. This is useful for
    rendering tests where small variations are expected.

    When images don't match, creates a diff image showing:
    - Red pixels: differences between images
    - Transparent pixels: matching areas
    """

    # Percentage of pixels that can differ before failing (0.0-100.0)
    PIXEL_DIFFERENCE_THRESHOLD = 1.0  # 1% of pixels can differ

    def _create_diff_image(
        self,
        current_image: Image.Image,
        baseline_image: Image.Image,
    ) -> Image.Image:
        """Create a visual diff image.

        Parameters
        ----------
        current_image : Image.Image
            The newly rendered image
        baseline_image : Image.Image
            The baseline snapshot image

        Returns
        -------
        Image.Image
            RGBA image with red pixels for differences and transparent for matches
        """
        # Create RGBA image for transparency support
        diff_image = Image.new(
            "RGBA",
            current_image.size,
            (0, 0, 0, 0),  # Transparent background
        )

        current_pixels = list(current_image.getdata())
        baseline_pixels = list(baseline_image.getdata())

        # Build diff: red for differences, original pixel with reduced alpha for matches
        diff_pixels = []
        for current_px, baseline_px in zip(current_pixels, baseline_pixels, strict=False):
            if current_px != baseline_px:
                # Difference: bright red
                diff_pixels.append((255, 0, 0, 255))
            # Match: original pixel with reduced alpha (~40% opaque)
            # Handle both RGB and RGBA pixels
            elif isinstance(current_px, int):
                # Grayscale
                diff_pixels.append((current_px, current_px, current_px, 100))
            elif len(current_px) == 3:
                # RGB
                r, g, b = current_px
                diff_pixels.append((r, g, b, 100))
            else:
                # RGBA - keep RGB, reduce alpha
                r, g, b, _ = current_px
                diff_pixels.append((r, g, b, 100))

        diff_image.putdata(diff_pixels)
        return diff_image

    def _save_diff_image(
        self,
        diff_image: Image.Image,
        snapshot_name: str,
    ) -> Path:
        """Save diff image to snapshots directory.

        Parameters
        ----------
        diff_image : Image.Image
            The diff image to save
        snapshot_name : str
            Name of the snapshot

        Returns
        -------
        Path
            Path where the diff was saved
        """
        # Create diffs directory in snapshots location
        diffs_dir = Path(__file__).parent / "__snapshots__" / "diffs"
        diffs_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename with uuid to avoid collisions
        unique_id = str(uuid.uuid4())[:8]
        diff_path = diffs_dir / f"{snapshot_name}_{unique_id}.diff.png"
        diff_image.save(diff_path)

        log.info(f"Saved diff image to: {diff_path}")
        return diff_path

    def matches(
        self,
        *,
        serialized_data,
        snapshot_data,
    ) -> bool:
        """Compare images with pixel-level tolerance.

        Creates a diff image when comparison fails.

        Parameters
        ----------
        serialized_data : SerializableData
            The newly rendered image data (bytes)
        snapshot_data : SerializableData
            The baseline snapshot image data (bytes)

        Returns
        -------
        bool
            True if images match within the tolerance threshold
        """
        try:
            # Load images
            current_image = Image.open(io.BytesIO(serialized_data))
            baseline_image = Image.open(io.BytesIO(snapshot_data))

            # Convert to same mode for comparison
            if current_image.mode != baseline_image.mode:
                baseline_image = baseline_image.convert(current_image.mode)

            # Check dimensions match
            if current_image.size != baseline_image.size:
                warnings.warn(
                    f"Image sizes differ: current {current_image.size} vs "
                    f"baseline {baseline_image.size}",
                    UserWarning,
                    stacklevel=1,
                )
                return False

            # Compare pixels
            current_pixels = list(current_image.getdata())
            baseline_pixels = list(baseline_image.getdata())

            total_pixels = len(current_pixels)
            differing_pixels = sum(
                1 for a, b in zip(current_pixels, baseline_pixels, strict=False) if a != b
            )

            percent_different = (differing_pixels / total_pixels * 100) if total_pixels > 0 else 0

            matches = percent_different <= self.PIXEL_DIFFERENCE_THRESHOLD

            if not matches:
                # Create and save diff image
                diff_image = self._create_diff_image(
                    current_image,
                    baseline_image,
                )
                diff_path = self._save_diff_image(diff_image, "mismatch")

                warnings.warn(
                    f"Image comparison failed: {percent_different:.2f}% of pixels differ "
                    f"(threshold: {self.PIXEL_DIFFERENCE_THRESHOLD}%) | "
                    f"See {diff_path.relative_to(Path(__file__).parent.parent)}",
                    UserWarning,
                    stacklevel=2,
                )

            return matches

        except Exception as e:
            log.error(f"Error comparing images: {e}")
            warnings.warn(
                f"Error comparing images: {e}",
                UserWarning,
                stacklevel=2,
            )
            # Fall back to binary comparison on error
            return bool(serialized_data == snapshot_data)


# Track failed snapshot tests for custom reporting
_failed_snapshots = []


def pytest_addoption(parser):
    parser.addoption(
        "--server-url",
        default=None,
        help="Server url.",
    )
    parser.addoption(
        "--web-url",
        default=None,
        help="Web url.",
    )
    parser.addoption(
        "--is-docker",
        action="store_true",
        default=False,
        help="Indicates if the app is running inside a Docker container.",
    )
    parser.addoption(
        "--connection-token",
        default=None,
        help="Connection token to an existing session.",
    )
    parser.addoption(
        "--launch-native",
        action="store_true",
        default=False,
        help="Indicates if the app should be launched natively.",
    )


def pytest_runtest_logreport(report):
    """Track failed snapshot tests for cleaner reporting."""
    if report.failed and hasattr(report, "longrepr"):
        # Check if this is a snapshot assertion failure
        longrepr_str = str(report.longrepr) if report.longrepr else ""

        if "snapshot" in longrepr_str.lower() and "assert" in longrepr_str.lower():
            # Find diff files for this test
            test_dir = Path(report.fspath).parent
            diffs_dir = test_dir / "__snapshots__" / "diffs"

            if diffs_dir.exists():
                diff_files = list(diffs_dir.glob("*.diff.png"))
                if diff_files:
                    # Get the most recently modified one (created during this test)
                    recent_diff = max(diff_files, key=lambda p: p.stat().st_mtime)
                    _failed_snapshots.append(
                        {
                            "test": report.nodeid,
                            "diff": str(recent_diff),  # Store as string for compatibility
                        }
                    )


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom summary for failed image snapshots."""
    if _failed_snapshots:
        terminalreporter.section("Image Snapshot Failures", sep="=")
        for entry in _failed_snapshots:
            test_name = entry["test"].split("::")[-1]
            diff_path = Path(entry["diff"])
            # Ensure absolute path
            if not diff_path.is_absolute():
                diff_path = Path(config.rootdir) / diff_path
            try:
                diff_rel = diff_path.relative_to(Path(config.rootdir))
            except ValueError:
                # If relative_to fails, just use the path as-is
                diff_rel = diff_path
            # Format: test_name -> diff_path
            terminalreporter.write_line(
                f"  {test_name:<50} -> {diff_rel}",
                bold=True,
                yellow=True,
            )
        terminalreporter.write_line("")


@pytest.fixture
def snapshot(snapshot):
    return snapshot.use_extension(ToleranceImageSnapshotExtension)


@pytest.fixture(scope="session", autouse=True)
def install_browser():
    """Ensure Playwright browsers are installed for the test session."""
    log.info("Installing Playwright browsers...")
    r = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        capture_output=True,
        text=True,
    )
    log.info(r.stdout)
    log.info(r.stderr)


@pytest.fixture(scope="session")
def rx_server():
    server_config = ServerLaunchConfig(num_threads=2)

    server_process = ResultExplorerServerProcess(server_config)
    server_process.start()

    yield server_process.url

    server_process.stop()


@pytest.fixture(scope="session")
def server_url(request):
    launch_native = request.config.getoption("--launch-native")
    if launch_native:
        return request.getfixturevalue("rx_server")

    return request.config.getoption("--server-url")


@pytest.fixture(scope="session")
def connection_token(request):
    return request.config.getoption("--connection-token")


@pytest.fixture(scope="session")
def web_url(request, server_url) -> str:
    web = request.config.getoption("--web-url")

    launch_native = request.config.getoption("--launch-native")
    if launch_native:
        server_url = request.getfixturevalue("rx_server")
        web = f"{server_url}/web"

    url = f"{web}?result_provider_name=Local&result_provider_url={server_url}"
    log.info(f"Using web URL: {url}")
    return url


@pytest.fixture(scope="session")
def is_docker(request):
    value = request.config.getoption("--is-docker")
    log.info(f"Is Docker: {value}")
    return value


INIT_SCRIPT = """
let config = {'enableScripting':true};
window.localStorage.setItem('config', JSON.stringify(config));
"""


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "permissions": ["clipboard-read", "clipboard-write"],
        "ignore_https_errors": True,
    }


@pytest.fixture
def rx(web_url: str, request) -> Client:
    connection_token = request.config.getoption("--connection-token")
    if connection_token is not None:
        log.info("Using provided connection token")
        return Client.connect_with_token(connection_token)

    context: BrowserContext = request.getfixturevalue("context")
    log.debug("Starting context for web session fixture")

    page = context.new_page()
    page.add_init_script(INIT_SCRIPT)
    page.goto(web_url)

    expect(page).to_have_title("Ansys Result Explorer")

    page.get_by_role("button", name="Scripting").click()
    page.get_by_label("Connection Token").click()

    connection_token = page.evaluate("navigator.clipboard.readText()")
    log.debug("Obtained connection token from web page")

    return Client.connect_with_token(connection_token)


@pytest.fixture(scope="session")
def data_directory(is_docker):
    if is_docker:
        return "/data"
    return os.path.abspath(os.path.join("tests", "data"))


def _get_result_path(data_directory, filename, docker: bool):
    path = Path(data_directory) / filename
    if docker:
        return path.as_posix()
    return str(path)


@pytest.fixture(scope="session")
def rst_multiple_connections(data_directory, is_docker) -> str:
    return _get_result_path(data_directory, "multiple_connections.rst", is_docker)


@pytest.fixture
def snapshot_settings() -> SnapshotSettings:
    """Provide clean snapshot settings suitable for testing.

    Returns settings with no timestamp, logo, legend, or solution name for
    reproducible, clean snapshot images.
    """
    return SnapshotSettings(
        show_time_stamp=False,
        show_logo=False,
        show_legend=False,
        show_solution_name=False,
        show_result_picker=False,
        transparent_background=False,
        background_color="#FFFFFF",
        height=300,
        width=300,
    )


@pytest.fixture
def multiple_connections_solution(rx, rst_multiple_connections) -> Generator[Solution, None, None]:
    sol = rx.create_solution(
        name="Test Solution",
        result_provider="Local",
        file_path=rst_multiple_connections,
    )
    assert sol.n_elements == 246
    assert sol.n_nodes == 844

    yield sol

    rx.delete_solution(sol)


@pytest.fixture(scope="session")
def rst_cp_transient(data_directory, is_docker) -> str:
    return _get_result_path(data_directory, os.path.join("cp_trans", "file.rst"), is_docker)


@pytest.fixture
def cp_transient_solution(rx, rst_cp_transient) -> Generator[Solution, None, None]:
    sol = rx.create_solution(
        name="Test Solution - CP Transient",
        result_provider="Local",
        file_path=rst_cp_transient,
    )
    assert sol.n_elements == 122
    assert sol.n_nodes == 406

    yield sol

    rx.delete_solution(sol)
