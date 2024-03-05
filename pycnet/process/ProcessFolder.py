"""Run the complete processing workflow on the target folder.

Generates spectrograms representing non-overlapping 12-s segments of
the audio, loads the appropriate version of the PNW-Cnet model and uses
it to generate class scores, then generates a set of apparent detections
to be reviewed and writes them to one or two CSV files.
"""

import os
import pycnet
import sys

def main():
    # target_dir, spectro_dir=None, cnet_version="v5", review_settings=None
    args = sys.argv
    help_message = """\nUsage:\nprocess_folder <arguments>
    Required arguments: 1. target directory (full path) 2. PNW-Cnet version ('v4' or 'v5').
    Optional arguments: 3. spectrogram directory (full path) 4. review_settings file (full path)
    e.g.
    process_folder F:\COA_22106 v5 G:\spectrograms 
    """
    if len(args) < 3:
        print(help_message)
    else:
        target_dir, cnet_version = args[1], args[2]
        if not os.path.exists(target_dir):
            print("\nTarget directory not found!\n")
            exit()
        elif cnet_version not in ["v4", "v5"]:
            print("PNW-Cnet version '{0}' not recognized!\nPlease enter 'v4' or 'v5'.\n".format(cnet_version))
            exit()
        else:
            if len(args) == 3:
                spectro_dir = None
                review_settings_file = None
            elif len(args) == 4:
                spectro_dir = args[3]
                review_settings_file=None
            else:
                spectro_dir, review_settings_file = args[3], args[4]
        pycnet.process.processFolder(target_dir=target_dir, cnet_version=cnet_version, spectro_dir=spectro_dir, review_settings=review_settings_file)
                
    
if __name__ == "__main__":
    main()