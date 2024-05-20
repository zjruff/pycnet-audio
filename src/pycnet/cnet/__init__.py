"""Defines characteristics of output from the PNW-Cnet model.

Defines the path to the trained model files and the full set of target
classes detected by each version.

Exports:

    v4_model_path
        Absolute path to the PNW-Cnet v4 trained model file.

    v5_model_path
        Absolute path to the PNW-Cnet v5 trained model file.

    v4_class_names
        List of strings representing class names for PNW-Cnet v4.

    v5_class_names
        List of strings representing class names for PNW-Cnet v5.

    target_classes
        Pandas.DataFrame listing the v4 and v5 class code, description,
        category, subcategory, taxonomic Class, Order, Family, Genus, 
        Species, and binomial scientific name (where applicable) for 
        each target class / sonotype detected by PNW-Cnet.

"""

import os
import pathlib
import pandas as pd


PACKAGEDIR = pathlib.Path(__file__).parent.absolute()


v4_model_path = os.path.join(PACKAGEDIR, "PNW-Cnet_v4_TF.h5")
v5_model_path = os.path.join(PACKAGEDIR, "PNW-Cnet_v5_TF.h5")


target_class_file = os.path.join(PACKAGEDIR, "target_classes.csv")
target_classes = pd.read_csv(target_class_file)


v4_class_names = ['AEAC', 'BRCA', 'BRMA', 'BUVI', 'CAGU', 'CALU', 'CAUS',
                  'CCOO', 'CHFA', 'CHMI', 'CHMI_IRREG', 'COAU', 'COAU2', 
                  'COCO', 'CYST', 'DEFU', 'DOG', 'DRPU', 'DRUM', 'FLY', 
                  'FROG', 'GLGN', 'HOSA', 'HYPI', 'INSP', 'IXNA', 'MEKE', 
                  'MYTO', 'NUCO', 'OCPR', 'ORPI', 'PAFA', 'PECA', 'PHNU', 
                  'PIMA', 'POEC', 'PSFL', 'SHOT', 'SITT', 'SPRU', 'STOC', 
                  'STOC_IRREG', 'STVA', 'STVA_IRREG', 'TADO1', 'TADO2', 
                  'TAMI', 'TUMI', 'WHIS', 'YARD', 'ZEMA']


v5_class_names = ['ACCO1', 'ACGE1', 'ACGE2', 'ACST1', 'AEAC1', 'AEAC2',
                  'Airplane', 'ANCA1', 'ASOT1', 'BOUM1', 'BRCA1', 
                  'BRMA1', 'BRMA2', 'BUJA1', 'BUJA2', 'Bullfrog', 
                  'BUVI1', 'BUVI2', 'CACA1', 'CAGU1', 'CAGU2', 'CAGU3',
                  'CALA1', 'CALU1', 'CAPU1', 'CAUS1', 'CAUS2', 'CCOO1', 
                  'CCOO2', 'CECA1', 'Chainsaw', 'CHFA1', 'Chicken', 
                  'CHMI1', 'CHMI2', 'COAU1', 'COAU2', 'COBR1', 'COCO1', 
                  'COSO1', 'Cow', 'Creek', 'Cricket', 'CYST1', 'CYST2', 
                  'DEFU1', 'DEFU2', 'Dog', 'DRPU1', 'Drum', 'EMDI1', 
                  'EMOB1', 'FACO1', 'FASP1', 'Fly', 'Frog', 'GADE1', 
                  'GLGN1', 'Growler', 'Gunshot', 'HALE1', 'HAPU1', 
                  'HEVE1', 'Highway', 'Horn', 'Human', 'HYPI1', 'IXNA1', 
                  'IXNA2', 'JUHY1', 'LEAL1', 'LECE1', 'LEVI1', 'LEVI2', 
                  'LOCU1', 'MEFO1', 'MEGA1', 'MEKE1', 'MEKE2', 'MEKE3', 
                  'MYTO1', 'NUCO1', 'OCPR1', 'ODOC1', 'ORPI1', 'ORPI2', 
                  'PAFA1', 'PAFA2', 'PAHA1', 'PECA1', 'PHME1', 'PHNU1', 
                  'PILU1', 'PILU2', 'PIMA1', 'PIMA2', 'POEC1', 'POEC2', 
                  'PSFL1', 'Rain', 'Raptor', 'SICU1', 'SITT1', 'SITT2', 
                  'SPHY1', 'SPHY2', 'SPPA1', 'SPPI1', 'SPTH1', 'STDE1', 
                  'STNE1', 'STNE2', 'STOC_4Note', 'STOC_Series', 
                  'Strix_Bark', 'Strix_Whistle', 'STVA_8Note', 
                  'STVA_Insp', 'STVA_Series', 'Survey_Tone', 'TADO1', 
                  'TADO2', 'TAMI1', 'Thunder', 'TRAE1', 'Train', 'Tree', 
                  'TUMI1', 'TUMI2', 'URAM1', 'VIHU1', 'Wildcat', 
                  'Yarder', 'ZEMA1', 'ZOLE1']
