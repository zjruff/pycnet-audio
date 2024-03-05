"""
'pycnet' library for audio processing

The purpose of this library is to provide a Python-based API and 
command-line tools for the PNW-Cnet audio classification model for
processing bioacoustics data on practical scales.

:copyright: (c) 2024 by Zachary Ruff
:license: GNU General Public License v3; see LICENSE for details.
"""

import os

from . import cnet
from . import file
from . import process
from . import prog
from . import review

# Change if necessary
sox_path = "C:\\Program Files (x86)\\sox-14-4-2"

assert os.path.isdir(sox_path)
assert os.path.exists(os.path.join(sox_path, "sox.exe"))

from importlib.metadata import version
__version__ = version("pycnet")
