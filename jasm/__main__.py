# __main__.py
# main entry point for the assembler.
# josiah bergen, december 2025

import os

from tap import Positional, Tap

from jasm.jasm import assemble
from jasm.util.logger import logger


class JasmArgumentParser(Tap):
    source: Positional[str]  # the file to assemble
    output: str = "a.bin"  # name of the output file
    nowarn: bool = False  # suppress warnings
    nowrite: bool = False  # suppress writing to ouput file
    nolink: bool = False  # enable low-level capabilities, makes binary unlinkable
    verbosity: int = logger.log_level.INFO  # verbosity level (0-3)


def check_files(file: str, output: str):
    """Check if the file is a valid JASM source file."""
    scope = "__main__.py:check_files()"

    # check if file is provided
    if not file:
        logger.fatal("no source file provided.", scope)

    if output and not output.endswith(".bin"):
        logger.warning(f"output file {output} will not have a valid binary extension. are you sure you want to continue?", scope, choice=True)

    # create output file if it doesn't exist
    if output and not os.path.exists(output):
        logger.info(f"creating output file {output}...")

        # create directory if it doesn't exist
        os.makedirs(os.path.dirname(output), exist_ok=True)
        open(output, "w").close()


def main():
    scope = "__main__.py:main()"

    args = JasmArgumentParser().parse_args()
    source = args.source
    output = args.output

    # initialize logger
    logger.set_level(args.verbosity)
    logger.set_warnings(not args.nowarn)
    logger.title("welcome to the jasm assembler!")
    logger.nl()

    options: dict[str, bool] = {
        "linkable": not args.nolink,
        "write": not args.nowrite,
    }

    try:
        check_files(source, output)
        logger.debug("init: everything looks good. starting assembly...")
        assemble(source, output, options)  # the magic!

    except KeyboardInterrupt:
        # give a nice exit message on ^C
        # this doesn't really prevent files from being corrupted or anything,
        # but at least it looks nice.
        logger.nl()
        logger.kill("keyboard interrupt", scope)

    exit(0)


if __name__ == "__main__":
    main()
