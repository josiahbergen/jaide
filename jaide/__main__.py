# __main__.py
# main entry point for the emulator.
# josiah bergen, january 2026

import argparse
import os
from .emulator import Emulator
from .util.logger import logger


def get_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(description="JAIDE emulator")
    arg_parser.add_argument("binary", nargs="?", default="", help="a binary file to load")
    return arg_parser.parse_args()


def check_files(file: str):
    scope = "__main__.py:check_files()"

    # check if file is provided
    if not file:
        logger.fatal("no source file provided.", scope)

    # check if file exists
    if not os.path.exists(file):
        logger.fatal("file does not exist.", scope)

    # check if file has a valid binary extension
    if not file.endswith(".bin"):
        logger.warning("file does not have a valid binary extension. are you sure you want to continue?", scope, choice=True)

    return True


def main():
    """ main entry point for the emulator. """
    args = get_args()
    scope = "__main__.py:main()"

    # initialize logger
    logger.title("welcome to the jaide emulator v0.0.1 (copyright 2026 Josiah Bergen)")
    logger.nl()

    binary = args.binary

    try:

        # create the emulator
        emulator = Emulator()

        if binary:
            check_files(binary)
            emulator.load_binary(binary)
        else:
            logger.warning("no binary file provided, you will need to load one manually.", scope)
        
        # pass control to the emulator
        emulator.repl()

    except KeyboardInterrupt:
        logger.nl()
        logger.kill("keyboard interrupt", scope)

    exit(0)

if __name__ == "__main__":
    main()
