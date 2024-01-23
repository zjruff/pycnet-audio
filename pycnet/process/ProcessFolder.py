"""Run the complete processing workflow on the target folder.

Generates spectrograms representing non-overlapping 12-s segments of
the audio, loads the appropriate version of the PNW-Cnet model and uses
it to generate class scores, then generates a set of apparent detections
to be reviewed and writes them to one or two CSV files.
"""

import os
import pycnet

def processFolder(target_dir, cnet_version, spectro_dir=None, review_settings=None):
    return