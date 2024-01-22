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

PACKAGEDIR = pathlib.Path(__file__).parents[1].absolute()
sys.path.append(str(PACKAGEDIR))

import pycnet

def makePredictions(target_dir, model_path, show_prog = False):
    """ Generate class scores for a set of images using the PNW-Cnet model.
    
    Returns a Pandas DataFrame, which R can handle more or less natively. The
    DataFrame has one column, Filename, for the names of the image files (not 
    full paths) and either 51 (PNW-Cnet v4) or 135 (PNW-Cnet v5) columns 
    containing the class scores.
    """
    v4_class_names = pycnet.cnet.v4_class_names
    v5_class_names = pycnet.cnet.v5_class_names

    image_paths = pycnet.file.findFiles(target_dir, ".png") 

    image_df = pd.DataFrame(data=image_paths, columns=["Filename"])

    # Generates batches of image data to be fed to the neural net. Rescales 
    # the 8-bit integer pixel values to float values in the range [0,1].
    image_generator = tf.keras.preprocessing.image.ImageDataGenerator(
        rescale = 1./255)
    
    predict_gen = image_generator.flow_from_dataframe(
        dataframe = image_df,
        directory = None,
        x_col = "Filename",
        y_col = None,
        target_size = (257, 1000),
        color_mode = 'grayscale',
        batch_size = 16,
        class_mode = None,
        shuffle = False)

    # TF tends to spit out some informational messages here, often in angry
    # red error-font, but usually they can be safely ignored.
    pnw_cnet_model = tf.keras.models.load_model(model_path)

    class_scores = pnw_cnet_model.predict(predict_gen, verbose = 1 if show_prog else 0)

    # Applies different column labels depending on the number of columns 
    # (i.e., target classes) in the class_scores dataframe. If it gets an 
    # unexpected number of columns (neither 51 nor 135) it just labels them 
    # sequentially.
    n_cols = class_scores.shape[1]
    if n_cols == 51:
        score_cols = v4_class_names
    elif n_cols == 135:
        score_cols = v5_class_names
    else:
        print("Warning: Prediction dataframe has unexpected number of columns. Cannot determine class names.")
        score_cols = ["Class_%s" % str(i).zfill(int(math.log10(n_cols))+1) for i in range(1, n_cols + 1)]

    predictions = pd.DataFrame(data = class_scores, columns = score_cols).round(decimals = 5)
    predictions.insert(loc = 0, column = "Filename", 
        value = [os.path.basename(path) for path in image_paths])

    return predictions

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
    
    predictions = makePredictions(target_dir, model_path, show_prog = True)
    
    print("\nFinished at {0}. {1} predictions generated.\n".format(time.strftime("%H:%M:%S"), len(predictions)))
    
    output_file = os.path.join(target_dir, "CNN_Predictions_{0}_{1}.csv".format(os.path.basename(target_dir), cnet_version))
    predictions.to_csv(path_or_buf = output_file, index = False)


if __name__ == "__main__":
    main()