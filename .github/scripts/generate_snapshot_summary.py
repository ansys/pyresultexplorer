#!/usr/bin/env python
"""Generate GitHub Actions summary with embedded snapshot diff images.

This script reads snapshot diff images from tests/__snapshots__/diffs/
and generates a markdown summary with base64-encoded images for display
in the GitHub Actions job summary.
"""

import base64
import os
from pathlib import Path


def main():
    """Generate snapshot diff summary and write to GITHUB_STEP_SUMMARY."""
    diffs_dir = Path("tests/__snapshots__/diffs")

    # Exit early if no diffs directory
    if not diffs_dir.exists():
        return

    diff_files = sorted(diffs_dir.glob("*.diff.png"))
    if not diff_files:
        return

    # Build markdown summary
    summary = "## Image Snapshot Failures\n\n"
    summary += f"Found {len(diff_files)} snapshot diff(s):\n\n"

    for diff_file in diff_files:
        # Extract test name from filename (format: mismatch_<uuid>.diff.png)
        test_name = diff_file.stem.replace(".diff", "").replace("_", " ")

        # Read and encode image
        with open(diff_file, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        # Add to summary
        summary += f"### {test_name}\n"
        summary += f"![snapshot diff](data:image/png;base64,{b64})\n\n"

    # Write to GitHub Actions step summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(summary)
    else:
        # Fallback for local testing
        print(summary)


if __name__ == "__main__":
    main()
