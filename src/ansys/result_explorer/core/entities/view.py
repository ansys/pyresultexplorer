"""View entity class."""

from __future__ import annotations

from .. import models
from .base import BaseEntity


class View(BaseEntity[models.View]):
    """Represents a result view in a solution."""

    @property
    def type(self):
        """View type (e.g., stress, displacement)."""
        return self._pb.type
