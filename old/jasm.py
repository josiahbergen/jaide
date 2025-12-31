import argparse
import os

from lark import Lark

from .assembler import generate_binary, resolve_labels
from .language.grammar import GRAMMAR
from .util.logger import Logger

# JASM assembler written in Python.
# Usage: python -m jasm <file> [-o <output file>] [-v <verbosity>]

# global logger object. used to log messages throughout the program.
global logger


def parse(file: str):
    """ Use Lark to parse the source file and return a parse tree. """
    scope = "jasm.py:parse()"

    logger.debug("parsing...")
    try:
        parser = Lark(GRAMMAR)
        tree = parser.parse(open(file).read())
    except Exception as e:
        logger.fatal(f"syntax error - {e}", scope)

    return tree


def assemble(file, output):

    # Parse the source file
    tree = parse(file)

    # Pass 1: expand macros and directives, then resolve labels
    labels = resolve_labels(tree)

    # Pass 2: generate binary
    binary = generate_binary(tree, labels)

    # write binary to output file
    with open(output, "wb") as f:
        f.write(binary)

    logger.debug(f"generated {len(binary)} bytes of binary code.")

    return len(binary)

