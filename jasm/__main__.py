# __main__.py
# main entry point for the assembler.
# josiah bergen, december 2025

import argparse
import os
from jasm.util.logger import logger
from jasm.jasm import assemble

def get_args():
    """
    Get and return command line arguments.
    """
    arg_parser = argparse.ArgumentParser(description="JASM assembler")
    arg_parser.add_argument("file", nargs="?", default="", help="the file to assemble")
    arg_parser.add_argument("-o", default="a.bin", help="name of the output file")
    arg_parser.add_argument("-nw", "--nowarn", action="store_true", help="suppress warnings")
    arg_parser.add_argument("-v", help="verbosity level (0-3)", default=logger.log_level.INFO, type=int)
    return arg_parser.parse_args()

def check_files(file: str, output: str):
    """ Check if the file is a valid JASM source file. """
    scope = "__main__.py:check_files()"

    # check if file is provided
    if not file:
        logger.fatal("no source file provided.", scope)

    # warn if output file already exists
    if output and not output.endswith(".bin"):
        logger.warning(f"output file {output} does not have a valid binary extension. are you sure you want to continue?", scope, choice=True)

    # create output file if it doesn't exist
    if output and not os.path.exists(output):
        logger.info(f"creating output file {output}...")
        open(output, "w").close()

    return True

def main():
    """ main entry point for the assembler. """
    args = get_args()
    scope = "__main__.py:main()"

    # initialize logger
    logger.set_level(args.v)
    logger.set_warnings(not args.nowarn)
    logger.title("welcome to the jasm assembler (v1.0.1)")
    logger.nl()

    file = args.file
    output = args.o

    try:
        check_files(file, output)
        logger.debug("init: everything looks good. starting assembly...")
        assemble(file, output) # the magic!

    except KeyboardInterrupt:
        # give a nice exit message on ^C
        # this doesn't really prevent files from being corrupted or anything,
        # but at least it looks nice.
        logger.nl()
        logger.kill("keyboard interrupt", scope)

    exit(0)

if __name__ == "__main__":
    main()
