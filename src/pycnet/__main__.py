"""Provides an interface for command-line processing of audio data.

This interface can be accessed by calling "python -m pycnet [args]" or 
simply "pycnet [args]"
"""

import os
import pycnet

def main():
    """Perform one or more processing operations on a folder.
    
    Intended to be run as a command-line script with behavior determined
    by one or more arguments. At a minimum, arguments should include a 
    mode (determines what the script actually does) and a target 
    directory containing the data you want to work with.
    
    usage:
    pycnet [mode] [target dir] [optional arguments]
    
    Run with the -h (help) flag, e.g. 'pycnet -h', to see all options.
    """

    valid_modes = ["process", "batch_process", "combine", "spectro", "predict", "review", "inventory", "rename", "cleanup"]

    args = pycnet.process.parsePycnetArgs()

    if not args.mode in valid_modes:
        print("\nMode '{0}' not recognized. Please use one of the following options:".format(args.mode))
        print('\n'.join(valid_modes))

    else:
        show_prog = not args.quiet_mode
        check_images = not args.skip_image_check
        auto_cleanup = args.auto_cleanup
        log_to_file = args.log_to_file
        combine_output = args.combine_output
        flac_mode = args.flac_mode
        

        if args.mode == "process":
            proc_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers]
            
            pycnet.process.processFolder(
                *proc_args, 
                review_settings=args.review_settings, 
                output_file=args.output_file, 
                log_to_file=log_to_file, 
                show_prog=show_prog, 
                cleanup=auto_cleanup, 
                check_images=check_images,
                flac_mode=flac_mode)


        elif args.mode == "batch_process":
            dir_list_file_path = args.target_dir

            try:
                with open(dir_list_file_path) as dir_list_file:
                    dir_list = [line.rstrip().replace('"', '') for line in dir_list_file.readlines()]
            except:
                print("\nCould not read list of target directories.\n")
                exit()

            dir_list = list(filter(os.path.isdir, dir_list))
            if len(dir_list) == 0:
                print("\nNo valid target directories provided.\n")
                exit()

            batch_args = [args.cnet_version, args.image_dir, args.n_workers]
            pycnet.process.batchProcess(
                dir_list, 
                *batch_args, 
                review_settings=args.review_settings, 
                log_to_file=log_to_file, 
                show_prog=show_prog, 
                cleanup=auto_cleanup, 
                check_images=check_images,
                combine_output=combine_output,
                flac_mode=flac_mode)


        elif args.mode == "combine":
            dir_list_file_path = args.target_dir

            try:
                with open(dir_list_file_path) as dir_list_file:
                    dir_list = [line.rstrip().replace('"', '') for line in dir_list_file.readlines()]
            except:
                print("\nCould not read list of target directories.\n")
                exit()

            dir_list = list(filter(os.path.isdir, dir_list))
            if len(dir_list) == 0:
                print("\nNo valid target directories provided.\n")
                exit()
            
            combine_args = [dir_list, args.cnet_version, args.review_settings]
            pycnet.process.combineOutputFiles(*combine_args, flac_mode=flac_mode)



        elif args.mode == "spectro":
            spectro_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers]
            pycnet.process.processFolder(
                *spectro_args, 
                log_to_file=log_to_file, 
                show_prog=show_prog, 
                cleanup=auto_cleanup,
                flac_mode=flac_mode)


        elif args.mode == "predict":
            predict_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir]
            pycnet.process.processFolder(
                *predict_args, 
                review_settings=args.review_settings, 
                show_prog=show_prog, 
                output_file=args.output_file, 
                log_to_file=log_to_file, 
                cleanup=auto_cleanup, 
                check_images=check_images,
                flac_mode=flac_mode)


        elif args.mode == "review":
            review_args = [args.mode, args.target_dir, args.cnet_version]
            pycnet.process.processFolder(
                *review_args, 
                review_settings=args.review_settings, 
                output_file=args.output_file, 
                log_to_file=log_to_file, 
                cleanup=auto_cleanup,
                flac_mode=flac_mode)


        elif args.mode == "inventory":
            inv_args = [args.target_dir]
            pycnet.file.inventoryFolder(
                *inv_args,
                flac_mode=flac_mode)


        elif args.mode == "rename":
            ext = ".flac" if flac_mode else ".wav"
            rename_args = [args.target_dir, ext, args.rename_prefix]
            pycnet.file.massRenameFiles(*rename_args)
            

        elif args.mode == "cleanup":
            cleanup_args = [args.target_dir, args.image_dir]
            pycnet.file.removeSpectroDir(*cleanup_args)


        else:
            pass

if __name__ == "__main__":
    main()
