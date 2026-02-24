# __main__.py
# main entry point for the emulator.
# josiah bergen, january 2026

import argparse
import os
import multiprocessing

from .emulator import Emulator
from .util.logger import logger

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
    multiprocessing.set_start_method("spawn", force=True)
    args = get_args()
    
    logger.title("welcome to the jaide emulator v0.0.1 (copyright 2026 Josiah Bergen)")
    logger.nl()

    shm, q, p = None, None, None

    try:
        if args.graphics:
            from .devices.graphics import start_graphics
            p, shm, q = start_graphics()
            logger.info(f"started graphics process (pid: {p.pid})")

        emulator = Emulator(shm_name=shm.name if shm else None, input_queue=q)

        if args.binary:
            check_files(args.binary)
            emulator.load_binary(args.binary)
            if args.run: emulator.run()
        else:
            logger.warning("no binary file provided, you will need to load one manually.", "__main__.py:main()")
        
        emulator.repl()

    except KeyboardInterrupt:
        logger.nl()
        logger.kill("keyboard interrupt", "__main__.py:main()")
    finally:
        if p and p.is_alive():
            p.terminate()
            p.join()
        if shm:
            shm.close()
            shm.unlink()
    
    exit(0)

if __name__ == "__main__":
    main()
