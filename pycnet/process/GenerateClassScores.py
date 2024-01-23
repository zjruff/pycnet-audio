""" 15 Jan 2024
Script to classify spectrograms using PNW-Cnet v4 or v5. Import this module to
use the makePredictions function directly or run as a script to classify
images in the folder specified, e.g.
python GenerateClassScores.py F:\Path\to\images v5
"""

import math 
import os
import pathlib 
import sys 
import time
import pandas as pd
import tensorflow as tf

import pycnet

def main():
    """ Script can be run through the Python interpreter (has to be in 
    r-reticulate or another Python environment / installation with compatible 
    packages) to make predictions directly. Run
    python GenerateClassScores.py E:\Path\to\Data F:\Path\to\PNW-Cnet_v4_TF.h5
    """
    target_dir, cnet_version = sys.argv[1], sys.argv[2]
    
    if cnet_version == "v4":
        model_path = pycnet.cnet.v4_model_path
    elif cnet_version == "v5":
        model_path = pycnet.cnet.v5_model_path
    else:
        print("Model version not recognized. Please specify 'v4' or 'v5'.")
        exit()
    
    print("\nMaking predictions on {0} starting at {1}...\n".format(target_dir, time.strftime("%H:%M:%S")))
    
    predictions = pycnet.cnet.generateClassScores(target_dir, model_path, show_prog = True)
    
    print("\nFinished at {0}. {1} predictions generated.\n".format(time.strftime("%H:%M:%S"), len(predictions)))
    
    output_file = os.path.join(target_dir, "{0}_{1}_class_scores.csv".format(os.path.basename(target_dir), cnet_version))
    predictions.to_csv(output_file, index = False)


if __name__ == "__main__":
    main()