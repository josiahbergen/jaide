# __main__.py
# main entry point for the emulator.
# josiah bergen, january 2026

import argparse
import os

from .emulator import Emulator
from .util.logger import logger
from .devices.graphics import Graphics

def get_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(description="JAIDE emulator")
    arg_parser.add_argument("binary", nargs="?", default="", help="a binary file to load")
    arg_parser.add_argument("-r", "--run", action="store_true", help="run the binary file immediately")
    arg_parser.add_argument("-g", "--graphics", action="store_true", help="automatically initialize the graphics controller")
    return arg_parser.parse_args()


def check_files(file: str):
    scope = "__main__.py:check_files()"

    # check if file is provided
    if not file:
        logger.fatal("no source file provided.", scope)

    # check if file exists
    if not os.path.exists(file):
        logger.fatal(f"file {file} does not exist.", scope)

    # check if file has a valid binary extension
    if not file.endswith(".bin"):
        logger.warning("file does not have a valid binary extension. are you sure you want to continue?", scope, choice=True)

    return True


def main():
    """ main entry point for the emulator. """
    args = get_args()
    
    logger.title("welcome to the jaide emulator v0.0.1 (copyright 2026 Josiah Bergen)")
    logger.nl()

    try: # main block to catch ctrl+c from everywhere

        emulator = Emulator()

        # load binary file if provided
        if args.binary:
            check_files(args.binary)
            emulator.load_binary(args.binary)
        else:
            logger.warning("no binary file provided, you will need to load one manually.", "__main__.py:main()")
        
        # start graphics if requested
        if args.graphics:
            graphics = Graphics(emulator.vram, emulator)
            graphics.start()

        emulator.repl()

    except KeyboardInterrupt:
        logger.nl()
        logger.kill("keyboard interrupt", "__main__.py:main()")
    
if __name__ == "__main__":
    main()
