"""
'pycnet' library for audio processing

The purpose of this library is to make the functionality of the PNW-Cnet
audio classification model available in Python with an accessible API for
processing bioacoustics data on practical scales.

:copyright: (c) 2024 by Zachary Ruff
:license: GNU General Public License v3; see LICENSE for details.
"""

import os

import pycnet.cnet as cnet
import pycnet.file as file
import pycnet.prog as prog
import pycnet.review as review

# Change if necessary
sox_path = "C:\\Program Files (x86)\\sox-14-4-2"

assert os.path.isdir(sox_path)
assert os.path.exists(os.path.join(sox_path, "sox.exe"))
