# __main__.py
# main entry point for the emulator.
# josiah bergen, january 2026

from .functions.create import create
from .functions.info import get_image_info
from .util import JFSArgs, logger

commands = {
    "create": create,
    "info": get_image_info,
}

def main():
    scope = "__main__.py:main()"
    args = JFSArgs().parse_args()

    # initalize logger
    logger.level = args.verbosity

    try:
        # execute command
        commands[args.command](args)
    except KeyError:
        logger.warn(f"unknown command {args.command}")
        logger.warn(f"valid commands are: {", ".join(commands.keys())}")
    except Exception as e:
        logger.error(f"{e}", scope)
        raise e

if __name__ == "__main__":
    main()
