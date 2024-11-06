"""'pycnet' library for audio processing

The purpose of this library is to provide a Python-based API and 
command-line tools for the PNW-Cnet audio classification model for
processing bioacoustics data on practical scales.

:copyright: (c) 2024 by Zachary J. Ruff
:license: GNU General Public License v3; see LICENSE for details.
"""

import os


from . import cnet
from . import file
from . import plot
from . import process
from . import prog
from . import review


from importlib.metadata import version
__version__ = version("pycnet-audio")
