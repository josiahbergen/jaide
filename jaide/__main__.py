# __main__.py
# main entry point for the emulator.
# josiah bergen, january 2026

import argparse
import os
from multiprocessing import Queue, Event

from .emulator import Emulator
from .util.logger import logger
from .devices.graphics import start_graphics_process
from .repl import REPL

def get_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(description="JAIDE emulator")
    _ = arg_parser.add_argument("binary", type=str, nargs="?", default="", help="a binary file to load")
    _ = arg_parser.add_argument("-r", "--run", action="store_true", help="run the binary file immediately")
    _ = arg_parser.add_argument("-g", "--graphics", action="store_true", help="automatically initialize the graphics controller")
    return arg_parser.parse_args()


def check_files(file: str) -> None:
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

def main():
    """ main entry point for the emulator. """
    args = get_args()

    logger.title("welcome to the jaide emulator v0.0.1 (copyright 2026 Josiah Bergen)")
    logger.nl()

    emulator = Emulator()

    # load binary file if provided
    if args.binary:
        check_files(args.binary)
        emulator.load_binary(args.binary)
    else:
        logger.warning("no binary file provided, you will need to load one manually.", "__main__.py:main()")

    if args.graphics:
        # set up IPC for graphics controller
        key_queue = Queue()
        gfx_stop_event = Event()

        gfx_proc = start_graphics_process(
            emulator.vram_shm.name,
            emulator.vram_shm.size,
            key_queue,
            gfx_stop_event,
        )

        # attach handles to emulator so it can poll input and shut graphics down
        emulator.key_queue = key_queue
        emulator.gfx_stop_event = gfx_stop_event
        emulator.gfx_proc = gfx_proc

    if args.run:
        logger.info("starting execution...")
        emulator.halted = False # unhalt
        emulator.run() # auto-run

    try:
        # start read-eval-print loop
        REPL(emulator)

    except KeyboardInterrupt:
        # the user has pressed ctrl+c inside the repl,
        # so we'll mirror the behavior of the quit command
        logger.info("bye! (signal from __main__)")
        emulator.shutdown()

if __name__ == "__main__":
    main()
