# operands.py
# ir instruction operand nodes.
# josiah bergen, march 2026

from .base import Operand, ExpressionNode
from .terminals import (
    NumberTerminal, 
    RegisterTerminal, 
    IdentifierTerminal
)

from ...language.isa import REGISTERS, MODES
from ...util.logger import logger


class RegisterOperand(Operand):
    def __init__(self, line: int, register: RegisterTerminal):
        super().__init__(line, MODES.REG)
        # adds a reference to the numeric register value
        self.register: REGISTERS = REGISTERS[register.value]

    def __str__(self) -> str:
        return f"{self.register}"

    def get_value(self) -> int:
        return self.register


class ImmediateOperand(Operand):
    def __init__(self, line: int, number: NumberTerminal):
        super().__init__(line, MODES.IMM)
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
    def __init__(self, line: int, identifier: IdentifierTerminal):
        super().__init__(line, MODES.RELATIVE)
        self.name: str = identifier.value

    def __str__(self) -> str:
        return f"{self.name}"        


class PointerOperand(Operand):
    def __init__(self, line: int, register: RegisterTerminal):
        super().__init__(line, MODES.REG_POINTER)
        self.register: REGISTERS = REGISTERS[register.value]

    def __str__(self) -> str:
        return f"[{self.register}]"

    def get_value(self) -> int:
        return self.register


class RelativePointerOperand(Operand):
    def __init__(self, line: int, label: IdentifierTerminal):
        super().__init__(line, MODES.REL_POINTER)
        self.label: str = label.value

    def __str__(self) -> str:
        return f"[{self.label}]"


class OffsetPointerOperand(Operand):
    def __init__(self, line: int, label: IdentifierTerminal, register: RegisterTerminal):
        super().__init__(line, MODES.OFF_POINTER)
        # we add two new values! wow!
        self.label: str = label.value
        self.register: REGISTERS = REGISTERS[register.value]

    def __str__(self) -> str:
        return f"[{self.label} + {self.register}]"

    def get_value(self) -> int:
        return self.register


class MacroArgumentOperand(Operand):
    def __init__(self, line: int, argument: IdentifierTerminal):
        super().__init__(line, MODES.NULL)
        # only valid inside macro body; refers to a provided argument by name.
        self.placeholder: str = argument.value

    def __str__(self) -> str:
        return f"%{self.placeholder}"


class ExpressionOperand(Operand):
    """Future: an expression operand. Not yet supported."""
    def __init__(self, line: int, expression: ExpressionNode):
        super().__init__(line, MODES.NULL)
        self.expression: str = expression.expression

    def __str__(self) -> str:
        return f"({self.expression})"

