# terminals.py
# ir terminal nodes.
# josiah bergen, march 2026

from typing import override

from ...util.logger import logger
from .base import IRNode


class Terminal(IRNode):
    def __init__(self, line: int, value: str):
        # dead simple. all terminals carry a value of some kind.
        # it is the responsibility of a higher-level parser to parse the value
        # into something more usable.
        super().__init__(line)
        self.value: str = value

    @override
    def __str__(self) -> str:
        # all subclasses inherit this, terminals are really only used
        # as an intermediate state during transformation to the final IR.
        return f"{type(self).__name__}: {self.value}"


class NormalizedTerminal(Terminal):
    def __init__(self, line: int, value: str):
        # normalize case to uppercase. useful for keywords,
        # directives, and mnemonics that should be case-insensitive.
        super().__init__(line, value)
        logger.verbose(f"normalized terminal: {value} -> {value.strip().upper()}")
        self.value: str = value.strip().upper()


class IdentifierTerminal(Terminal): ...


class StringTerminal(Terminal):
    def __init__(self, line: int, value: str):
        super().__init__(line, value)
        self.value: str = value[1:-1]  # quotes


class NumberTerminal(Terminal):
    # leave parsing to the operand parser.
    ...


class RegisterTerminal(NormalizedTerminal): ...


class KeywordTerminal(NormalizedTerminal): ...


class DirectiveTerminal(NormalizedTerminal): ...


class MnemonicTerminal(NormalizedTerminal): ...
