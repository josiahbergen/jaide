# argparser.py
# custom argument parsing suite
# josiah bergen, january 2026

import argparse
from typing import Any
from jasm.util.logger import logger

class ArgumentParser(argparse.ArgumentParser):
    pass

    def print_usage(self) -> None:
        logger.title("usage: jasm <file> [-o <output>] [-nw] [-v <verbosity>]")
        logger.nl()
        for name, arg in self.args.items():
            logger.info(f"{name}: {arg['help']}")
            logger.nl()

