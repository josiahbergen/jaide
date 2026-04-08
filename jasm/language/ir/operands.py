# operands.py
# ir instruction operand nodes.
# josiah bergen, march 2026

import os

from ...language.isa import MODES, REGISTERS
from ...util.logger import logger
from .base import ExpressionNode, Operand
from .terminals import IdentifierTerminal, NumberTerminal, RegisterTerminal


class RegisterOperand(Operand):
    def __init__(self, line: int, filename: str, register: RegisterTerminal):
        super().__init__(line, filename, MODES.REG)
        # adds a reference to the numeric register value
        self.register: REGISTERS = REGISTERS[register.value]

    def __str__(self) -> str:
        return f"{self.register}"

    def get_value(self) -> int:
        return self.register


class ImmediateOperand(Operand):
    def __init__(self, line: int, filename: str, number: NumberTerminal):
        super().__init__(line, filename, MODES.IMM)
        self.string: str = number.value # string representation
        self.value: int = int(self.string, 0)
        
    def __str__(self) -> str:
        return f"{self.string}"


    def get_value(self) -> int:
        if self.value > 0xFFFF:
            logger.fatal(f"immediate value {self.value} on line {self.line} is too large. must be less than 0xFFFF.", "ir.py:ImmediateOperand.get_value()")
        if self.value < 0:
            logger.fatal(f"immediate value {self.value} on line {self.line} must be greater than 0.", "ir.py:ImmediateOperand.get_value()")
        return self.value


class LabelOperand(Operand):
    def __init__(self, line: int, filename: str, identifier: IdentifierTerminal):
        super().__init__(line, filename, MODES.RELATIVE)

        name = identifier.value.upper().strip() # normalize
        already_mangled = "__" in name and "_" not in name.split("__")[0]  
        filename = os.path.basename(filename).split(".")[0].upper() # the actual name, no path or extension

        self.name: str = f"{filename}__{name}" if not already_mangled else name # mangle with filename
        self.short_name: str = name if not already_mangled else name.split("__")[-1]

        logger.verbose(f"label: {self.short_name} -> {self.name} (in {filename}, {"not " if not already_mangled else ""}already mangled)")

    def __str__(self) -> str:
        return f"{self.name}"


class PointerOperand(Operand):
    def __init__(self, line: int, filename: str, register: RegisterTerminal):
        super().__init__(line, filename, MODES.REG_POINTER)
        self.register: REGISTERS = REGISTERS[register.value]

    def __str__(self) -> str:
        return f"[{self.register}]"

    def get_value(self) -> int:
        return self.register


class RelativePointerOperand(Operand):
    def __init__(self, line: int, filename: str, label: IdentifierTerminal):
        super().__init__(line, filename, MODES.REL_POINTER)
        self.label: str = label.value.upper().strip() # normalize

    def __str__(self) -> str:
        return f"[{self.label}]"


class OffsetPointerOperand(Operand):
    def __init__(self, line: int, filename: str, label: IdentifierTerminal, register: RegisterTerminal):
        super().__init__(line, filename, MODES.OFF_POINTER)
        # we add two new values! wow!
        self.label: str = label.value.upper().strip() # normalize
        self.register: REGISTERS = REGISTERS[register.value]

    def __str__(self) -> str:
        return f"[{self.label} + {self.register}]"

    def get_value(self) -> int:
        return self.register


class MacroArgumentOperand(Operand):
    def __init__(self, line: int, filename: str, argument: IdentifierTerminal):
        super().__init__(line, filename, MODES.NULL)
        # only valid inside macro body; refers to a provided argument by name.
        self.placeholder: str = argument.value

    def __str__(self) -> str:
        return f"%{self.placeholder}"


class ExpressionOperand(Operand):
    """Future: an expression operand. Not yet supported."""
    def __init__(self, line: int, filename: str, expression: ExpressionNode):
        super().__init__(line, filename, MODES.NULL)
        self.expression: str = expression.expression

    def __str__(self) -> str:
        return f"({self.expression})"

