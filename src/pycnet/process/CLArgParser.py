"""Define acceptable command-line arguments when running pycnet as a
module or through console scripts.

Functions:
- parsePycnetArgs: create a parser for command-line arguments to pycnet
- correctPycnetArgs: correct arguments and provide sensible defaults
(not currently in use)

"""

import argparse
import multiprocessing as mp
import os


def parsePycnetArgs():
    """Define command-line options for the 'pycnet' console script.
    
    Sequestered here for neatness.
    
    Arguments:
    None (reads args from stdin)
    
    Returns:
    - args: an argparse.Namespace object containing command-line 
    arguments in an accessible form
    """
    n_cores = mp.cpu_count()

    parser = argparse.ArgumentParser(description="Perform one or more processing operations on a folder.")

    parser.add_argument("mode", metavar="MODE", type=str,
        choices=["rename", "inventory", "spectro", "predict", "review", "process", "cleanup", "test"], 
        help="Operation to be performed. Options: 'inventory' (default), 'rename', 'spectro', 'predict', 'review', 'process', 'cleanup'.", default="inventory")

    parser.add_argument("target_dir", metavar="TARGET_DIR", type=str, help="Path to the directory containing .wav files to be processed.")

    parser.add_argument("-c", dest="cnet_version", type=str, choices=["v4", "v5"], default="v5",
        help="Version of PNW-Cnet to use when generating class scores. Options: 'v5' (default) or 'v4'.")

    parser.add_argument("-i", dest="image_dir", type=str,
        help="Path to the directory where spectrogram images will be stored. Will be created if it does not already exist. Default: a folder called Temp under target dir.")

    parser.add_argument("-w", dest="n_workers", type=int,
        help="Number of worker processes to use when generating spectrograms. Default: number of available cores (currently {0}).".format(n_cores))

    parser.add_argument("-r", dest="review_settings", type=str,
        help="Path to file containing settings to use when generating the review file.")

    parser.add_argument("-o", dest="output_file", type=str,
        help="Manually specify output filename.")

    parser.add_argument("-q", dest="quiet_mode",
        help="Quiet mode (suppress progress bars and informational messages).")

    # parser.add_argument("-a", dest="auto_cleanup",
        # help="Remove spectrogram image files and temporary folders when class scores have been generated.")

    args = parser.parse_args()
    
    return args


def correctPycnetArgs(orig_args):
    """Check arguments for audio processing and correct as necessary.
    
    The main() function in pycnet.process.__init__ is kind of a 
    switchboard for all the various tasks that the package is meant
    to perform. User calls the program as 'pycnet' and chooses a mode.
    Depending on the mode chosen, different arguments will be relevant.
    In almost all cases the user will need to provide a target directory
    containing the audio data (or image data) to be processed.
    
    Think it's more straightforward to accept all the arguments that the
    user provides and put the relevant ones in an ordered list that will
    be fed to the appropriate function. The main function of 
    pycnet.__main__ now does exactly that, rendering this one redundant.
    
    valid modes: rename, inventory, spectro, predict, review, process, cleanup, config
    
    Arguments:
    - orig_args: an argparse Namespace containing the unaltered command
    line arguments
    
    """
    corrected_args = {}
    corrected_args["target_dir"] = orig_args.target_dir
    if orig_args.mode == "process":
        if not orig_args.n_workers:
            corrected_args["n_workers"] = mp.cpu_count()

    return corrected_args