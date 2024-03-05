"""Define behavior of 'pycnet' in relation to command-line arguments."""

import argparse
import multiprocessing as mp
import os


def parsePycnetArgs():
    """Define command-line options for the 'pycnet' console script.
    
    Inevitably a bit of a mess so sequestered here.
    """
    n_cores = mp.cpu_count()
    
    parser = argparse.ArgumentParser(description="Perform one or more processing operations on a folder.")

    parser.add_argument("mode", metavar="MODE", type=str,
        choices=["rename", "inventory", "spectro", "predict", "review", "process", "cleanup"], 
        help="Operation to be performed. Options: 'inventory' (default), 'rename', 'spectro', 'predict', 'review', 'process', 'cleanup', 'config'.", default="inventory")

    parser.add_argument("target_dir", metavar="TARGET_DIR", type=str, help="Path to the directory containing .wav files to be processed.")
    
    parser.add_argument("-v", dest="cnet_version", type=str, choices=["v4", "v5"], default="v5",
        help="Version of PNW-Cnet to use when generating class scores. Options: 'v5' (default) or 'v4'.")
    
    parser.add_argument("-s", dest="spectro_dir", type=str, 
        help="Path to the directory where spectrogram images will be stored. Will be created if it does not already exist. Default: a folder called Temp under target dir.")
    
    parser.add_argument("-o", dest="output_dir", type=str,
        help="Path to the directory where output CSV files will be saved. Will be created if it does not already exist. Default: same as target dir.")
    
    parser.add_argument("-w", dest="n_workers", type=int,
        help="Number of worker processes to use when generating spectrograms. Default: number of available cores (currently {0}).".format(n_cores))
    
    parser.add_argument("-r", dest="review_settings", type=str,
        help="Path to file containing settings to use when generating the review file.")
    
    parser.add_argument("-q", dest="quiet_mode",
        help="Quiet mode (suppress progress bars and informational messages).")
    
    parser.add_argument("-c", dest="auto_cleanup",
        help="Remove spectrogram image files and temporary folders when class scores have been generated.")

    args = parser.parse_args()
    
    return args


def checkPycnetArgs(args):
    """Check whether all required args for the chosen mode are present.
    
    The main() function in pycnet.process.__init__ is kind of a 
    switchboard for all the various tasks that the package is meant
    to perform. User calls the program as 'pycnet' and chooses a mode.
    Depending on the mode chosen, different arguments will be relevant.
    In almost all cases the user will need to provide a target directory
    containing the audio data (or image data) to be processed.
    
    Need a dang flowchart for this
    
    valid modes: rename, inventory, spectro, predict, review, process, cleanup, config
    
    """
    return True