"""Generate one or more audio files containing mostly random noise
and a few examples of the synthetic survey tone played during northern
spotted owl surveys. Run these files through the pycnet processing 
pipeline to verify everything is working properly.

"""

import os
import pandas as pd
import pycnet
import shutil
import subprocess


def generateToneFile(output_dir):
    """Generate a 10 minute clip containing silence except for survey
    tones at 00:40, 03:25, and 07:50, normalized to -30 dB.
    Complete survey tones will be in part_004, part_018, and part_040.
    """
    sox_path = "sox"
    sox_cmd_init = "{0} -n -r 32000 -c 1 -b 16 -e signed-integer".format(sox_path)

    tone_clip_path = os.path.join(output_dir, "Tone_Clip_raw.wav")
    noise_clip_path = os.path.join(output_dir, "Noise_Clip_raw.wav")
    combined_clip_path = os.path.join(output_dir, "Combined_Clip_norm.wav")

    tone_synth_cmd = "synth 0.5 sine 500 : synth 0.25 sine 0 : synth 0.5 sine 2000 : synth 0.25 sine 0 : synth 0.5 sine 1000"
    tone_clip_synth_cmd = "{0} {1} synth 40 sine 0 : {2} : synth 163 sine 0 : {2} : synth 263 sine 0 : {2} : synth 128 sine 0".format(sox_cmd_init, tone_clip_path, tone_synth_cmd)
    subprocess.call(tone_clip_synth_cmd)

    noise_clip_synth_cmd = "{0} {1} synth 600 pinknoise".format(sox_cmd_init, noise_clip_path)
    subprocess.call(noise_clip_synth_cmd)

    combined_clip_synth_cmd = "sox -m {0} {1} {2} norm -30".format(tone_clip_path, noise_clip_path, combined_clip_path)
    subprocess.call(combined_clip_synth_cmd)

    os.remove(tone_clip_path)
    os.remove(noise_clip_path)

    return combined_clip_path


def main():
    print("\nWelcome to pycnet! You are using version {0}.".format(pycnet.__version__))

    test_dir = os.path.join(os.getcwd(), "pycnet_test")

    hex_dir = os.path.join(test_dir, "NON_99999")
    stn_dir = os.path.join(hex_dir, "Stn_Z")
    try:
        os.makedirs(stn_dir)
        print("\nA temporary test folder has been created at\n{0}.".format(test_dir))
    except:
        print("\nFailed to create temporary test folder!")
        exit()
    
    test_clip = generateToneFile(stn_dir)
    if os.path.exists(test_clip):
        print("Test audio file successfully generated.")
    else:
        print("Failed to create test audio file!")
        exit()

    pycnet.file.massRenameFiles(hex_dir, ".wav")

    pycnet.process.processFolder("process", hex_dir, n_workers=1, show_prog=False)

    kscope_file_path = os.path.join(hex_dir, "NON_99999_v5_review_kscope.csv")
    if os.path.exists(kscope_file_path):
        kscope_df = pd.read_csv(kscope_file_path)
        rev_lines = kscope_df.shape[0]
        if list(kscope_df.PART) == ["part_004", "part_018", "part_040"]:
            print("\nTest complete. pycnet appears to be working correctly. Hooray!\n")
            rm_temp_dirs = input("Remove files and folders created for this test? [Y/n] ")
            if rm_temp_dirs.upper() != "N":
                os.system("rmdir /s /q {0}".format(test_dir))
    else:
        print("Did not find output file {0}.".format(os.path.basename(kscope_file_path)))
        exit()


if __name__ == "__main__":
    main()