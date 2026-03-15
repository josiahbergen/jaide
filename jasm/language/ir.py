# language/ir.py
# intermediate representation for the JASM language.
# josiah bergen, december 2025

import os
from enum import IntEnum

from ..util.logger import logger
from .isa import INSTRUCTIONS, REGISTERS, MODES

class IRNode:
    """ Super simple base node class for the IR. """
    
    def __init__(self, line: int):
        self.line = line
        self.pc = 0 # where the instruction will be placed in the binary

    def get_size(self) -> int:
        scope = "ir.py:IRNode.get_size()"
        logger.warning(f"get_size() not implemented for {type(self)}", scope)
        return 0

    def get_bytes(self) -> bytearray:
        scope = "ir.py:IRNode.get_bytes()"
        logger.warning(f"get_bytes() not implemented for {type(self)}", scope)
        return bytearray()

    def __str__(self) -> str:
        scope = "ir.py:IRNode.__str__()"
        logger.warning(f"__str__() not implemented for {type(self)}", scope)
        return f"{type(self).__name__} at line {self.line}"


# operand classes

class Operand(IRNode):

    def __init__(self, line: int):
        super().__init__(line)

    def get_integer_value(self) -> int:
        scope = "ir.py:Operand.get_integer_value()"
        logger.warning(f"get_integer_value() not implemented for {type(self)}", scope)
        return 0


class RegisterOperand(Operand):

    def __init__(self, line: int, register: REGISTERS):
        super().__init__(line)
        self.register: REGISTERS = register

    def __str__(self) -> str:
        return f"{self.register}"


class Constant(Operand):

    def __init__(self, line: int, value: str):
        super().__init__(line)
        self.value: str = value

class ImmediateOperand(Constant):

    def __init__(self, line: int, value: str):
        super().__init__(line, value)
        self.value: str = self.value.strip().lower()
        self.base: int = 16 if self.value.startswith("0x") else 2 if self.value.startswith("b") else 10

    def __str__(self) -> str:
        return f"{self.value}"


class LabelOperand(Operand):
    def __init__(self, line: int, label: str):
        super().__init__(line)
        self.label: str = label

    def __str__(self) -> str:
        return f"{self.label}"


class PointerOperand(RegisterOperand):
    """ A node representing a memory operand, i.e. [reg]"""
    def __init__(self, line: int, register: REGISTERS):
        super().__init__(line, register)

    def __str__(self) -> str:
        return f"[{self.register}]"


class OffsetAddressOperand(Operand):
    """ A node representing a offset address operand, i.e. [imm16 + reg]"""
    def __init__(self, line: int, label: str, register: REGISTERS):
        super().__init__(line)
        self.label: str = label
        self.register: REGISTERS = register

    def __str__(self) -> str:
        return f"[{self.label} + {self.register}]"

class MacroArgumentOperand(Operand):
    """Only valid inside macro body; refers to a parameter by name."""
    def __init__(self, line: int, name: str):
        super().__init__(line)
        self.name: str = name

    def __str__(self) -> str:
        return f"%{self.name}"


class ExpressionOperand(Operand):
    """Future: an expression operand. Not yet supported."""
    def __init__(self, line: int, expression: str):
        super().__init__(line)
        self.expression: str = expression

    def __str__(self) -> str:
        return f"({self.expression})"

# top-level nodes

class InstructionNode(IRNode):
    """ A node representing an instruction. """

    def __init__(self, line: int, mnemonic: str, operands: list[Operand]):
        super().__init__(line)

        self.mnemonic: INSTRUCTIONS = INSTRUCTIONS[mnemonic.upper()]
        self.operands: list[Operand] = operands

        # set later by a semantic pass
        self.addressing_mode: int | None = None
        self.size: int | None = None
 
    def __str__(self) -> str:
        return f"{self.mnemonic.name} {', '.join([str(op) for op in self.operands])}"

class LabelNode(IRNode):

    def __init__(self, line: int, name: str):
        super().__init__(line)
        self.name: str = name

    def __str__(self) -> str:
        return f"{self.name}:"

class ImportDirectiveNode(IRNode):

    def __init__(self, line: int, filename: str):
        super().__init__(line)
        scope = "ir.py:ImportDirectiveNode.__init__()"

        try:
            # normalize to improve robustness of circular import detection
            filename = os.path.normcase(os.path.realpath(filename))
        except Exception as e:
            logger.fatal(f"invalid filename: {e}", scope)
        self.filename: str = filename

    def __str__(self) -> str:
        return f"import {self.filename}"


class DataDirectiveNode(IRNode):

    class Type(IntEnum):
        NUMBER = 0
        STRING = 1

    def __init__(self, line: int, items: list[tuple[Type, str]]):
        super().__init__(line)
        self.items: list[tuple[DataDirectiveNode.Type, str]] = items


    def __str__(self) -> str:
        strs = [f"{d[1]}" if d[0] == DataDirectiveNode.Type.NUMBER else f'"{d[1]}"' for d in self.items]
        return f"data {', '.join(strs)}"

class MacroDefinitionNode(IRNode):

    def __init__(self, line: int, name: str, args: list[str], body: list[IRNode]):
        super().__init__(line)
        self.name: str = name
        self.args: list[str] = args # placeholder identifiers for the arguments
        self.body: list[IRNode] = body

    def __str__(self) -> str:
        return f"macro {self.name} {', '.join(self.args)} ({len(self.body)} body nodes)"

class MacroCallNode(IRNode):

    def __init__(self, line: int, name: str, args: list[Operand]):
        super().__init__(line)
        self.name: str = name # macro being called
        self.args: list[Operand] = args # real values to substitute for the placeholders

    def __str__(self) -> str:
        return f"macro call: {self.name} with {', '.join([str(op) for op in self.args])}"