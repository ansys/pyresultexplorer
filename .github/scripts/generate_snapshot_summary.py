"""Generate HTML report with embedded snapshot diff images.

This script reads snapshot diff images from tests/__snapshots__/diffs/
and generates an HTML report with base64-encoded images for viewing
in a browser after downloading from GitHub Actions artifacts.
"""

import base64
import os
from pathlib import Path


def main():
    """Generate HTML snapshot diff report."""
    diffs_dir = Path("tests/__snapshots__/diffs")
    report_file = Path("snapshot_diffs_report.html")

    # Exit early if no diffs directory
    if not diffs_dir.exists():
        print("No diffs directory found")
        return

    diff_files = sorted(diffs_dir.glob("*.diff.png"))
    if not diff_files:
        print("No diff images found")
        return

    # Build HTML report
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Snapshot Diff Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f6f8fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #24292f;
            border-bottom: 1px solid #d0d7de;
            padding-bottom: 10px;
        }}
        .summary {{
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 20px;
            color: #57606a;
        }}
        .diff-container {{
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            margin: 20px 0;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .diff-title {{
            font-weight: 600;
            color: #d1242f;
            margin-bottom: 12px;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .diff-icon {{
            font-size: 20px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            margin-top: 8px;
        }}
        .meta {{
            color: #57606a;
            font-size: 13px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #eaeef2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Snapshot Diff Report</h1>
        <div class="summary">
            <strong>{len(diff_files)} snapshot diff(s) found</strong> in <code>tests/__snapshots__/diffs/</code>
        </div>
"""

    for i, diff_file in enumerate(diff_files, 1):
        # Extract test name from filename (format: mismatch_<uuid>.diff.png)
        test_name = diff_file.stem.replace(".diff", "").replace("_", " ").title()

        # Read and encode image
        with open(diff_file, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        # Add to HTML
        html += f"""        <div class="diff-container">
            <div class="diff-title">
                <span class="diff-icon">🔴</span>
                <span>{i}</span>
            </div>
            <img src="data:image/png;base64,{b64}" alt="Snapshot diff: {test_name}">
            <div class="meta"><strong>File:</strong> {diff_file.name}</div>
        </div>
"""

    html += """    </div>
</body>
</html>
"""

    # Write HTML file
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html)

    # Add link to GitHub Actions step summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        summary = "## 📸 Image Snapshot Failures\n\n"
        summary += f"**{len(diff_files)} snapshot diff(s)** generated. "
        summary += "Download the **snapshot_diffs_report.html** artifact to view all diffs.\n"
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(summary)

    print(f"Generated HTML report: {report_file}")


if __name__ == "__main__":
    main()
