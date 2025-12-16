import argparse
import os

from util import Logger, GRAMMAR
from lark import Lark
from assembler import resolve_labels, generate_binary

# JASM assembler written in Python.
# Usage: python jasm.py <file> [-o <output file>] [-d <debug>] 

logger = None


def parse(file):
    logger.debug("Parsing...")
    try:
        parser = Lark(GRAMMAR)
        tree = parser.parse(open(file).read())
    except Exception as e:
        logger.error(f"Syntax error: {e}")
        exit(1)

    return tree


def assemble(file, output):

    logger.info(f"Assembling {file}...")

    # Parse the source file
    tree = parse(file)
    
    # Pass 1: Resolve labels
    labels = resolve_labels(tree, logger)
    
    # Pass 2: Generate binary
    binary = generate_binary(tree, labels, logger)
    
    # Write binary to output file
    with open(output, 'wb') as f:
        f.write(binary)
    
    logger.debug(f"Generated {len(binary)} bytes of binary code.")

    return len(binary)

def main():
    argparser = argparse.ArgumentParser(description="JASM assembler")
    argparser.add_argument("file", nargs="?", default="", help="The file to assemble")
    argparser.add_argument("-o", "--output", default="a.bin", help="The output file")
    argparser.add_argument("-v", "--verbosity", help="Verbosity level", default=Logger.Level.INFO, type=int)
    args = argparser.parse_args()

    # initialize logger
    global logger
    logger = Logger(args.verbosity)
    logger.title("JASM Assembler v1.0")
    logger.info("")

    # check if file is provided
    if not args.file:
        logger.error("No file(s) provided. Exiting...")
        exit(1)

    # check if file exists
    if not os.path.exists(args.file):
        logger.error(f"File {args.file} does not exist. Exiting...")
        exit(1)

    # check if file is an assembly file
    if not args.file.endswith(".jasm"):
        logger.error(f"File {args.file} is not a JASM file. Exiting...")
        exit(1)
    
    logger.debug("Init looks good. Starting assembly...")

    # the magic
    size = assemble(args.file, args.output)

    if logger.level == Logger.Level.DEBUG:
        logger.flush_debug()
        logger.info("")
    logger.info(f"Wrote {size} bytes to {args.output}.")
    logger.success("Assembly complete! Yay!")
    logger.info("")

    exit(0)

if __name__ == "__main__":
    main()