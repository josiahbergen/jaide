# language/ir.py
# intermediate representation for the JASM language.
# josiah bergen, december 2025

from .constants import OPCODES, OPERAND_TYPES, OPERAND_TYPE_TO_STRING
from ..util.logger import logger

class IRNode:
    """ Really simple base node class for the IR. """

    def __init__(self, line: int):
        self.line = line
        self.children = []

    def add_child(self, child: 'IRNode'):
        self.children.append(child)


class OperandNode(IRNode):
    def __init__(self, line: int, type: str, value: str):
        super().__init__(line)
        scope = "ir.py:OperandNode.__init__()"

        self.type = OPERAND_TYPES[type]
        self.value = value # just stored as a string for now

        # validate the operand type
        if type not in OPERAND_TYPES.keys():
            logger.fatal(f"invalid operand type on line {line}: {type}", scope)

    def __str__(self):
        return f"{OPERAND_TYPE_TO_STRING[self.type]} {self.value}"


class InstructionNode(IRNode):


    def __init__(self, line: int, mnemonic: str, operands: list[OperandNode]):
        super().__init__(line)

        self.mnemonic = mnemonic
        self.opcode = OPCODES[mnemonic]
        self.operands = operands
        # self.addressing_mode = get_addressing_mode(mnemonic, operands)
        # self.size = get_instruction_size(mnemonic, operands)

        self.validate_instruction_semantics()

    def assert_num_operands(self, required_num: int):
        scope = "ir.py:InstructionNode.assert_num_operands()"
        if len(self.operands) != required_num:
            logger.fatal(f"instruction {self.mnemonic} on line {self.line} requires {required_num} operands (got {len(self.operands)})", scope)

    def assert_operand_types(self, expected_types: list[int]):
        scope = "ir.py:InstructionNode.assert_operand_types()"
        if not all(op.type in expected_types for op in self.operands):
            logger.fatal(f"instruction {self.mnemonic} on line {self.line} has invalid operand types", scope)

    def validate_instruction_semantics(self):
        scope = "ir.py:InstructionNode.validate_instruction_semantics()"
        match self.mnemonic:
            case "SEC" | "CLC" | "CLZ" | "HALT" | "NOP":
                self.assert_num_operands(0)
            case "INT":
                self.assert_num_operands(1)
                self.assert_operand_types([OPERAND_TYPES["NUMBER"]])
            case "POP" | "INC" | "DEC" | "NOT":
                self.assert_num_operands(1)
                self.assert_operand_types([OPERAND_TYPES["REGISTER"]])
            case "PUSH":
                self.assert_num_operands(1)
                self.assert_operand_types([OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"]])
            case "MOVE" | "ADD" | "ADDC" | "SUB" | "SUBB" | "SHL" | "SHR" | "AND" | "OR" | "NOR" | "XOR" | "CMP" | "INB" | "OUTB":
                self.assert_num_operands(2)
                self.assert_operand_types([OPERAND_TYPES["REGISTER"], OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"]])
            case "JUMP" | "JZ" | "JNZ" | "JC" | "JNC":
                self.assert_num_operands(1)
                self.assert_operand_types([OPERAND_TYPES["LABELNAME"], OPERAND_TYPES["NUMBER"], OPERAND_TYPES["REGISTER_PAIR"]])
            case "LOAD" | "STORE":
                self.assert_num_operands(2)
                self.assert_operand_types([OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"], OPERAND_TYPES["REGISTER_PAIR"]])
            case _:
                logger.fatal(f"unknown instruction {self.mnemonic} on line {self.line}", scope)

    def __str__(self):
        return f"instruction: {self.mnemonic} (line {self.line}) with {len(self.operands)} operands: {", ".join([str(op) for op in self.operands])}"


class ImportDirectiveNode(IRNode):
    def __init__(self, line: int, filename: str):
        super().__init__(line)
        self.filename = filename

        # remove quotes from the beginning and end of the filename
        if self.filename.startswith('"') and self.filename.endswith('"'):
            self.filename = self.filename[1:-1]

    def __str__(self):
        return f"import directive: {self.filename}"


class DataDirectiveNode(IRNode):
    def __init__(self, line: int, data: list[tuple[str, str]]):
        super().__init__(line)
        self.data = data

    def __str__(self):
        return f"data directive: {", ".join([f"{value} ({type})" for value, type in self.data])}"

class LabelNode(IRNode):
    def __init__(self, line: int, label: str):
        super().__init__(line)
        self.label = label
        self.position = None # will be set later

    def __str__(self):
        return f"label: {self.label} at position {self.position}"