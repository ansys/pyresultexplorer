"""Logger for the ansys-result-explorer-core package."""

import logging
import sys

log = logging.getLogger("ansys-result-explorer-core")

log.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
log.addHandler(handler)
