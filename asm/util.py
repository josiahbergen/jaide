import sys

import colorama

# EBNF-like grammar.
GRAMMAR = r"""
    ?start: line* # Programs must begin with a start label

    ?line: instr # Lines contain an instruction or a label
         | label

    label: LABELNAME ":"

    instr: MNEMONIC operand_list?

    operand_list: operand ("," operand)*

    ?operand: REGISTER_PAIR
            | REGISTER
            | NUMBER
            | LABELNAME

    COMMENT: /;.*/

    # priorities for token matching
    # higher number = higher priority

    # instructions are always matched first
    # (i.e. will never be interpreted as a label, etc.)
    MNEMONIC.100: /(LOAD|STORE|MOVE|PUSH|POP|ADD|ADDC|SUB|SUBB|INC|DEC|SHL|SHR|AND|OR|NOR|NOT|XOR|INB|OUTB|CMP|SEC|CLC|CLZ|JMP|JZ|JNZ|JC|JNC|INT|HALT|NOP)\b/i

    # Register pairs are matched before single registers
    REGISTER_PAIR.90: /(A|B|C|D|X|Y|SP|PC|Z|F|MB|STS):(A|B|C|D|X|Y|SP|PC|Z|F|MB|STS)/i
    REGISTER.80: /(A|B|C|D|X|Y|SP|PC|Z|F|MB|STS)\b/i

    NUMBER.20: /0[xX][0-9a-fA-F]+/i
          | /[bB][01]+/
          | /[0-9]+/
    LABELNAME.10: /[A-Za-z_][A-Za-z0-9_]*/

    # Lark provides common definitions for whitespace.
    %import common.WS
    # Ignore comments and whitespace.
    %ignore WS
    %ignore COMMENT
"""


class Logger:
    class Level:
        VERBOSE: int = 3
        DEBUG: int = 2
        INFO: int = 1
        ERROR: int = 0

    def __init__(self, level: int):
        colorama.init()
        self.level: int = level
        self.debug_buffer: list[str] = []
        self.debug_count: int = 0
        self.flush_interval: int = 0

    def verbose(self, message: str):
        if self.level >= self.Level.VERBOSE:
            formatted_message = (
                colorama.Fore.YELLOW + "[DEBUG] " + colorama.Fore.RESET + message
            )
            self.debug_buffer.append(formatted_message)
            self.debug_count += 1

            if self.debug_count >= self.flush_interval:
                self.flush_debug()

    def debug(self, message: str):
        if self.level >= self.Level.DEBUG:
            formatted_message = (
                colorama.Fore.YELLOW + "[DEBUG] " + colorama.Fore.RESET + message
            )
            self.debug_buffer.append(formatted_message)
            self.debug_count += 1

            if self.debug_count >= self.flush_interval:
                self.flush_debug()

    def flush_debug(self):
        if self.debug_buffer:
            for msg in self.debug_buffer:
                print(msg, flush=False)
            _ = sys.stdout.flush()  # Flush stdout after all buffered messages
            self.debug_buffer.clear()
            self.debug_count = 0

    def small(self, message: str):
        if self.level >= self.Level.INFO:
            print(colorama.Fore.BLACK + message + colorama.Fore.RESET)

    def info(self, message: str):
        if self.level >= self.Level.INFO:
            print(colorama.Fore.RESET + message + colorama.Fore.RESET)

    def error(self, message: str):
        self.flush_debug()
        print(colorama.Fore.RED + "ERROR: " + message + colorama.Fore.RESET)

    def success(self, message: str):
        if self.level >= self.Level.INFO:
            print(
                colorama.Back.GREEN
                + colorama.Fore.BLACK
                + message
                + colorama.Fore.RESET
                + colorama.Back.RESET
            )

    def title(self, message: str):
        if self.level >= self.Level.INFO:
            print(
                colorama.Back.BLUE
                + colorama.Fore.BLACK
                + message
                + colorama.Fore.RESET
                + colorama.Back.RESET
            )
