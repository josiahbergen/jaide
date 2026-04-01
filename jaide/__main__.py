# __main__.py
# main entry point for the emulator.
# josiah bergen, january 2026

import os

from tap import Tap

from .emulator import Emulator
from .repl import REPL
from .util.logger import logger


class EmulatorArgumentParser(Tap):
    binary: str = ""   # a binary file to load
    run: bool = False  # run the binary file immediately
    verbosity: int = logger.log_level.INFO  # verbosity level (0-3)

    # devices
    pit: bool = False  
    rtc: bool = False
    graphics: bool = False
    disk: bool = False

    def configure(self):
        self.add_argument("binary", nargs="?")
        self.add_argument("-r", "--run")
        self.add_argument("-v", "--verbosity")

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
    args = EmulatorArgumentParser().parse_args()

    devices: dict[str, bool] = {
        "pit": args.pit,
        "rtc": args.rtc,
        "graphics": args.graphics,
        "disk": args.disk,
    }

    emulator = Emulator(verbosity=args.verbosity, enabled_devices=devices)

    # load binary file if provided
    if args.binary:
        check_files(args.binary)
        emulator.load_binary(args.binary)
    else:
        logger.warning("no binary file provided, you will need to load one manually.", "__main__.py:main()")

    if args.run:
        logger.info("starting execution...")
        emulator.run() # auto-run

    try:
        # start read-eval-print loop
        REPL(emulator)

    except KeyboardInterrupt:
        # the user has pressed ctrl+c inside the repl,
        # so we'll mirror the behavior of the quit command
        logger.info("\nbye! (signal from __main__)")
        emulator.shutdown()

if __name__ == "__main__":
    main()
