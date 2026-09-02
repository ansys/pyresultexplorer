# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Custom snapshot extensions for pytest and syrupy."""

import io
import logging
import uuid
import warnings
from pathlib import Path

from PIL import Image
from syrupy.extensions.image import PNGImageSnapshotExtension

log = logging.getLogger(__name__)


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
