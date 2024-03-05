""" Defining characteristics of the PNW-Cnet model (v4 and v5) """

import os
import pathlib
import pandas as pd

PACKAGEDIR = pathlib.Path(__file__).parent.absolute()

v4_model_path = os.path.join(PACKAGEDIR, "PNW-Cnet_v4_TF.h5")
v5_model_path = os.path.join(PACKAGEDIR, "PNW-Cnet_v5_TF.h5")

target_class_file = os.path.join(PACKAGEDIR, "target_classes.csv")
target_classes = pd.read_csv(target_class_file)

v5_class_names = sorted(target_classes["v5_Code"])
v4_classes = target_classes[pd.notnull(target_classes["v4_Code"])]
v4_class_names = sorted(v4_classes["v4_Code"])
