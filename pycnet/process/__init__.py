"""Functions to provide a higher-level interface for typical processing 
tasks. Common processing workflows should be accessible as simple CLI
commands using console_scripts entry points from the top-level pycnet 
package.
Functions:
1. makeFileInventory: Build an inventory of .wav files in the target 
folder.
2. generateSpectrograms: Generate a set of spectrograms representing 
segments of the audio.
3. generateClassScores: Process an existing set of spectrograms using
the PNW-Cnet model.
4. makeReviewTable: Filter raw class scores to get a set of apparent 
detections of one or more target classes.
5. processFolder: Do all of the above in one go.
"""

import os
import pycnet

