# util.py
# utility functions and classes used throughout the project.
# josiah bergen, april 2026

import sys
from typing import Iterable

import colorama as cl
from colorama import Fore as f
from tap import Positional, Tap

from .constants import BLOCK_SIZE


class Logger:

    class log_level:
        VERBOSE: int = 3
        DEBUG: int = 2
        INFO: int = 1
        ERROR: int = 0

    def __init__(self, level: int = log_level.DEBUG):
        cl.init()
        self.level: int = level

    def info(self, message: str):
        """ Print an info message. Only prints if level is INFO or higher. """
        if self.level >= self.log_level.INFO:
            formatted = f"{f.LIGHTBLACK_EX}jfs: {f.RESET}{message}"
            print(formatted)
            
    def debug(self, message: str):
        """ Print a debug message. Only prints if level is DEBUG or higher. """
        if self.level >= self.log_level.DEBUG:
            formatted = f"{f.LIGHTBLACK_EX}jfs: {f.RESET}{message}"
            print(formatted)

    def verbose(self, message: str):
        """ Print a verbose message. Only prints if level is VERBOSE or higher. """
        if self.level >= self.log_level.VERBOSE:
            formatted = f"{f.LIGHTBLACK_EX}jfs: {message}{f.RESET}"
            print(formatted)

    def error(self, message: str, scope: str):
        """ Print non-fatal error message. """
        formatted = f"{f.RED}err {f.LIGHTBLACK_EX}in {scope}:{f.RESET} {message}"
        print(f"{formatted}")

    def fatal(self, message: str, scope: str, newline: bool = True):
        """ Print error message and exit the program with error status. """
        formatted = f"{f.RED}err {f.LIGHTBLACK_EX}in {scope}:{f.RESET} {message}"
        print(f"{'\n' if newline else ''}{formatted}", end="\n\n")
        sys.exit(1)  # exit with error

    def warn(self, message: str, scope: str | None = None) -> None:
        """ Print a warning message. Only prints if level is INFO or higher. """
        scope = (scope + ": ") if scope else ""
        formatted = f"{f.YELLOW}warn: {f.RESET}{scope}{message}"
        print(formatted)

    def success(self, message: str):
        """ Print a success message. Only prints if level is DEBUG or higher. """
        if self.level >= self.log_level.INFO:
            formatted = f"{f.GREEN}success!{f.RESET} {message}"
            print(formatted)


class JFSArgs(Tap):
    command: Positional[str]                # the command to execute (create, info)
    image: str = "disk.img"                 # the image file to create/inspect
    files: list[str] = []                   # files to add to the image
    verbosity: int = Logger.log_level.INFO  # verbosity level (0-3)

    def configure(self):
        self.add_argument("-i", "--image")
        self.add_argument("-f", "--files")
        self.add_argument("-v", "--verbosity")


logger = Logger()

def block_offset(block_num: int) -> int:
    return block_num * BLOCK_SIZE


def decode_packed_null_terminated(words: Iterable[int]) -> str:

    out: list[str] = []
    for word in words:
        lo = word & 0xFF
        if lo == 0:
            break
        out.append(chr(lo))

        hi = (word >> 8) & 0xFF
        if hi == 0:
            break
        out.append(chr(hi))

    return "".join(out)