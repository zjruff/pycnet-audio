""" Defining characteristics of the PNW-Cnet model (v4 and v5) """

import math 
import os
import pathlib
import time
import pandas as pd
import tensorflow as tf

from .. import file

PACKAGEDIR = pathlib.Path(__file__).parent.absolute()


v4_model_path = os.path.join(PACKAGEDIR, "PNW-Cnet_v4_TF.h5")
v5_model_path = os.path.join(PACKAGEDIR, "PNW-Cnet_v5_TF.h5")


target_class_file = os.path.join(PACKAGEDIR, "target_classes.csv")
target_classes = pd.read_csv(target_class_file)


v5_class_names = sorted(target_classes["v5_Code"])
v4_classes = target_classes[pd.notnull(target_classes["v4_Code"])]
v4_class_names = sorted(v4_classes["v4_Code"])


def generateClassScores(target_dir, model_path, show_prog=False):
    """Generate class scores for a set of spectrograms using PNW-Cnet. 

    Returns a Pandas DataFrame, which R can handle more or less natively. The
    DataFrame has one column Filename for the names of the image files and 
    either 51 (PNW-Cnet v4) or 135 (PNW-Cnet v5) columns for class scores.
    
    Arguments:
    <target_dir>: directory containing spectrograms in the form of .png
    image files; these images will be classified by the PNW-Cnet model
    <model_path>: path to either PNW-Cnet_v4_TF.h5 or PNW-Cnet_v5_TF.h5
    <show_prog>: whether to show a text-based progress bar as the model
    makes predictions on batches of images
    """

    # Find all the PNG files in the directory tree
    image_paths = file.findFiles(target_dir, ".png")
    image_df = pd.DataFrame(data=image_paths, columns=["Filename"])

    # The generator uses the dataframe of image paths to feed batches of image
    # data to the neural net after rescaling the 8-bit integer pixel values to 
    # floating-point in the range [0,1].
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

    # Spits out a few informational and warning messages which can be safely ignored.
    pnw_cnet_model = tf.keras.models.load_model(model_path)

    # Progress bar is kind of obnoxious when running in RStudio (prints a separate
    # line for each step) but still probably helpful on balance. 
    class_scores = pnw_cnet_model.predict(predict_gen, verbose = 1 if show_prog else 0)

    # Function applies different column labels depending on the number of columns
    # (i.e., target classes) in the class_scores dataframe. If it gets an unexpected
    # number of columns (neither 51 nor 135) it just labels them sequentially.
    n_cols = class_scores.shape[1]
    if n_cols == 51:
        score_cols = v4_class_names
    elif n_cols == 135:
        score_cols = v5_class_names
    else:
        print("Warning: Prediction dataframe has unexpected number of columns. Cannot determine class names.")
        score_cols = ["Class_%s" % str(i).zfill(int(math.log10(n_cols))+1) for i in range(1, n_cols + 1)]

    predictions = pd.DataFrame(data=class_scores, columns=score_cols).round(decimals = 5)
    predictions.insert(loc=0, column="Filename", 
        value=[os.path.basename(path) for path in image_paths])

    return predictions
    
