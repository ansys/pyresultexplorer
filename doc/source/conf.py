"""Sphinx documentation configuration file."""

import os
import pathlib
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path for autodoc to find modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ansys_sphinx_theme import get_version_match

from ansys.result_explorer.core import __version__

SKIP_GALLERY = os.environ.get("PYRX_DOC_SKIP_GALLERY", "1").lower() in ("1", "true")

# Project information
project = "ansys-result-explorer-core"
copyright = f"(c) {datetime.now().year} ANSYS, Inc. All rights reserved"
author = "ANSYS, Inc."
release = version = __version__
cname = os.getenv("DOCUMENTATION_CNAME", "https://pyresultexplorer.docs.pyansys.com")
switcher_version = get_version_match(__version__)

# Select desired logo, theme, and declare the html title
html_theme = "ansys_sphinx_theme"
html_short_title = html_title = "pyresultexplorer"

# specify the location of your github repo
html_theme_options = {
    "github_url": "https://github.com/ansys-internal/pyresultexplorer",
    "show_prev_next": False,
    "show_breadcrumbs": True,
    "additional_breadcrumbs": [
        ("PyAnsys", "https://docs.pyansys.com/"),
    ],
    "switcher": {
        "json_url": f"https://{cname}/versions.json",
        "version_match": switcher_version,
    },
    "check_switcher": False,
    "logo": "pyansys",
}

# Sphinx extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "numpydoc",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_gallery.gen_gallery",
    "sphinx_design",
]

# autosummary configuration
autosummary_generate = True
autosummary_imported_members = True

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    # kept here as an example
    # "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
    # "numpy": ("https://numpy.org/devdocs", None),
    # "matplotlib": ("https://matplotlib.org/stable", None),
    # "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    # "pyvista": ("https://docs.pyvista.org/", None),
    # "grpc": ("https://grpc.github.io/grpc/python/", None),
}

# sphinx-design configuration
sd_fontawesome_latex = True

# numpydoc configuration
numpydoc_show_class_members = False
numpydoc_xref_param_type = True

# Consider enabling numpydoc validation. See:
# https://numpydoc.readthedocs.io/en/latest/validation.html#
numpydoc_validate = True
numpydoc_validation_checks = {
    "GL06",  # Found unknown section
    "GL07",  # Sections are in the wrong order.
    "GL08",  # The object does not have a docstring
    "GL09",  # Deprecation warning should precede extended summary
    "GL10",  # reST directives {directives} must be followed by two colons
    "SS01",  # No summary found
    "SS02",  # Summary does not start with a capital letter
    # "SS03", # Summary does not end with a period
    "SS04",  # Summary contains heading whitespaces
    # "SS05", # Summary must start with infinitive verb, not third person
    "RT02",  # The first line of the Returns section should contain only the
    # type, unless multiple values are being returned"
}

if SKIP_GALLERY:
    # Generate the gallery without executing the code. The gallery will not
    # contain the output of the code cells.
    # This is useful for more quickly building the documentation.
    gallery_filename_pattern = "<MATCH NOTHING>"
else:
    gallery_filename_pattern = r".*\.py"

examples_dirs_base = pathlib.Path(__file__).parent.parent.parent / "examples"
gallery_dirs_base = pathlib.Path(__file__).parent / "examples"

# sphinx gallery options
sphinx_gallery_conf = {
    # convert rst to md for ipynb
    "pypandoc": True,
    # path to your examples scripts
    "examples_dirs": [str(examples_dirs_base)],
    # path where to save gallery generated examples
    "gallery_dirs": [str(gallery_dirs_base)],
    # Pattern to search for example files
    "filename_pattern": gallery_filename_pattern,
    # Remove the "Download all examples" button from the top level gallery
    "download_all_examples": False,
    # Sort gallery example by filename instead of number of lines (default)
    "within_subsection_order": "FileNameSortKey",
    # directory where function granular galleries are stored
    "backreferences_dir": "api/_gallery_backreferences",
    # Modules for which function level galleries are created.
    "doc_module": ("ansys.result_explorer.core"),
    "exclude_implicit_doc": {"ansys\\.result_explorer\\.core\\._.*"},  # ignore private submodules
    # "image_scrapers": (DynamicScraper(), "matplotlib"),
    "ignore_pattern": r"__init__\.py",
    "thumbnail_size": (320, 240),
    "remove_config_comments": True,
}

print(sphinx_gallery_conf)

# static path
html_static_path = ["_static"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# Keep these while the repository is private
linkcheck_ignore = [
    "https://github.com/ansys-internal/pyresultexplorer/*",
    "https://pyresultexplorer.docs.pyansys.com/version/stable/*",
    "https://pypi.org/project/ansys-result-explorer-core",
]

# If we are on a release, we have to ignore the "release" URLs, since it is not
# available until the release is published.
if switcher_version != "dev":
    linkcheck_ignore.append(
        f"https://github.com/ansys-internal/pyresultexplorer/releases/tag/v{__version__}"
    )
