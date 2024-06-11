"""Provides an interface for command-line processing of audio data.

This interface can be accessed by calling "python -m pycnet [args]" or 
simply "pycnet [args]"
"""

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

    valid_modes = ["process", "spectro", "predict", "review", "inventory", "rename", "cleanup"]

    args = pycnet.process.parsePycnetArgs()

    if not args.mode in valid_modes:
        print("\nMode '{0}' not recognized. Please use one of the following options:".format(args.mode))
        print('\n'.join(valid_modes))

    else:
        show_prog = not args.quiet_mode
        auto_cleanup = args.auto_cleanup
        log_to_file = args.log_to_file
        
        if args.mode == "process":
            proc_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers]
            pycnet.process.processFolder(*proc_args, review_settings=args.review_settings, output_file=args.output_file, log_to_file=log_to_file, show_prog=show_prog, cleanup=auto_cleanup)

        elif args.mode == "spectro":
            spectro_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers]
            pycnet.process.processFolder(*spectro_args, log_to_file=log_to_file, show_prog=show_prog, cleanup=auto_cleanup)

        elif args.mode == "predict":
            predict_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir]
            pycnet.process.processFolder(*predict_args, review_settings=args.review_settings, show_prog=show_prog, output_file=args.output_file, log_to_file=log_to_file, cleanup=auto_cleanup)

        elif args.mode == "review":
            review_args = [args.mode, args.target_dir, args.cnet_version]
            pycnet.process.processFolder(*review_args, review_settings=args.review_settings, output_file=args.output_file, log_to_file=log_to_file, cleanup=auto_cleanup)

        elif args.mode == "inventory":
            inv_args = [args.target_dir]
            pycnet.file.inventoryFolder(*inv_args)

        elif args.mode == "rename":
            rename_args = [args.target_dir, "wav"]
            pycnet.file.massRenameFiles(*rename_args)
            
        elif args.mode == "cleanup":
            cleanup_args = [args.target_dir, args.image_dir]
            pycnet.file.removeSpectroDir(*cleanup_args)

        else:
            pass

if __name__ == "__main__":
    main()
