from sphinx_mdolab_theme.config import *  # noqa F403

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import sys
import os

sys.path.insert(0, os.path.abspath("../"))

# -- Project information -----------------------------------------------------
project = "baseClasses"

# -- General configuration -----------------------------------------------------
# Built-in Sphinx extensions are already contained in the imported variable
# here we add external extensions, which must also be added to requirements.txt
# so that RTD can import and use them
extensions.extend(["numpydoc"])  # noqa F405

# mock import for autodoc
autodoc_mock_imports = ["numpy", "pygeo", "mpi4py"]
