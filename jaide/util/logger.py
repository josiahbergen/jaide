# util/logger.py
# logger class used throughout the project.
# josiah bergen, december 2025

import sys

import colorama as cl
from colorama import Back as b
from colorama import Fore as f


class Logger:

    class log_level:
        VERBOSE: int = 3
        DEBUG: int = 2
        INFO: int = 1
        ERROR: int = 0


    def __init__(self, level: int, warnings: bool = True):
        cl.init()
        self.level: int = level
        self.warnings: bool = warnings


    def set_level(self, level: int):
        self.level = level


    def set_warnings(self, warnings: bool):
        self.warnings = warnings


    def verbose(self, message: str):
        """ Print a verbose message. Only prints if level is VERBOSE or higher. """
        if self.level >= self.log_level.VERBOSE:
            formatted = f"{f.BLACK}----- {message}{f.RESET}"
            print(formatted)


    def debug(self, message: str):
        """ Print a debug message. Only prints if level is DEBUG or higher. """
        if self.level >= self.log_level.DEBUG:
            formatted = f"{f.BLACK}===== {f.RESET}{message}"
            print(formatted)


    def info(self, message: str):
        """ Print an info message. Only prints if level is INFO or higher. """
        if self.level >= self.log_level.INFO:
            print(f"{message}")


    def error(self, message: str):
        """ Print non-fatal error message. """
        formatted = f"{f.RED}err:{f.RESET} {message}"
        print(formatted)

    def fatal(self, message: str, scope: str):
        """ Print error message and exit the program with error status. """
        # formatted = b.RED + f.BLACK + "\n fatal! " + b.RESET + f.RED + " " + scope + ": " + message + f.RESET

        newline = '\n' if self.level >= self.log_level.INFO else ''
        formatted = f"{newline}{b.RED}{f.BLACK} fatal! {b.RESET}{f.RED} {scope}: {message}{f.RESET}"

        print(formatted)
        sys.exit(1)  # exit with error


    def kill(self, message: str, scope: str):
        """ Print error message and exit the program with non-error status. """
        # formatted = f"\n{b.RED}{f.BLACK} stopped! {b.RESET}{f.RESET} {scope}: {message}{f.RESET}"

        # newline = '\n' if self.level >= self.log_level.INFO else ''
        formatted = f"\n{b.RED}{f.BLACK} {message} {b.RESET}{f.RESET} process killed at {scope} {f.RESET}"
        print(formatted)
        sys.exit(0)  # exit with non-error


    def success(self, message: str):
        """ Print a success message. Only prints if level is DEBUG or higher. """
        if self.level >= self.log_level.DEBUG:
            formatted = f"{f.GREEN}{message}{f.RESET}"
            # formatted = f"{f.GREEN}{message}{f.RESET}"
            print(formatted)


    def title(self, message: str):
        """ Print a title. Only prints if level is DEBUG or higher. """
        if self.level >= self.log_level.DEBUG:
            formatted = b.BLUE + f.BLACK + message + f.RESET + b.RESET
            print(formatted)


    def warning(self, message: str, scope: str | None = None, choice: bool = False) -> None:
        """ Print a warning message. Only prints if level is INFO or higher. """
        if not self.warnings:
            return
        
        scope = scope or ""

        # formatted = f"{b.YELLOW} {b.RESET} {f.YELLOW}warn:{f.RESET}{f.BLACK} {scope}: {f.YELLOW}{message}{f.RESET}"
        # formatted = f"{b.YELLOW} {b.RESET} {f.YELLOW}warn: {message}{f.BLACK} at {scope}{f.RESET}"
        formatted = f"{f.YELLOW}warn: {f.RESET}{scope}: {message}"
        end_char = '' if choice else '\n'
        print(formatted, end=end_char)
        if not choice:
            return
        if not self.yesno():
            self.kill("abort", scope)


    def yesno(self, message: str | None = None) -> bool:
        """ Print a yes/no question and return a boolean answer. """
        prompt = (message or "") + " (y/n): "

        while not (ans := input(prompt).lower().strip()).startswith(("y", "n")):
            print("invalid answer.", end="")
        return ans.startswith("y")


    def nl(self):
        """ Print a newline. """
        if self.level >= self.log_level.DEBUG:
            print("")

logger = Logger(Logger.log_level.INFO, warnings=True)