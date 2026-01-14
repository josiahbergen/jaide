# language/ir.py
# intermediate representation for the JASM language.
# josiah bergen, december 2025

from .constants import OPCODES, OPERAND_TYPES, OPERAND_TYPE_TO_STRING, REGISTERS, ADDRESSING_MODES, ADDRESSING_MODE_TO_SIZE
from ..util.logger import logger


class IRNode:
    """ Really simple base node class for the IR. """
    
    # class variable to store resolved labels
    labels: dict[str, int] = {}

    def __init__(self, line: int):
        self.line = line
        self.pc = 0 # where the instruction will be placed in the binary


    def get_size(self) -> int:
        scope = "ir.py:IRNode.get_size()"
        logger.warning(f"get_size() not implemented for node type {type(self)}", scope)
        return 0


    def get_bytes(self) -> bytearray:
        return bytearray()


    def pretty_bit_string(self, bytes: bytearray):
        return " ".join([f"{i:08b}" for i in bytes])


    def short_string(self) -> str:
        return f"generic IRNode at line {self.line}"


    def __str__(self) -> str:
        return f"Base IRNode at line {self.line}"


class OperandNode(IRNode):
    """ A node representing an operand. """

    def __init__(self, line: int, type_string: str, value: str):
        super().__init__(line)
        scope = "ir.py:OperandNode.__init__()"

        self.type: int = OPERAND_TYPES[type_string]
        self.type_string: str = type_string
        
        # stored as a string which is parsed during code generation
        # this probably sucks
        self.value: str = value

        # validate the operand type
        if type_string not in OPERAND_TYPES.keys():
            logger.fatal(f"invalid operand type on line {line}: {type_string}", scope)


    def get_integer_value(self) -> int:
        scope = "ir.py:OperandNode.get_integer_value()"

        if self.type == OPERAND_TYPES["REGISTER"]:
            reg = REGISTERS.get(self.value.upper())
            if reg is None:
                logger.fatal(f"unknown register on line {self.line}: {reg}", scope)
            logger.verbose(f"get_integer_value: register {self.value} -> {reg}")
            return reg

        elif self.type == OPERAND_TYPES["REGISTER_PAIR"]:
            regs = self.value.split(":")
            if len(regs) != 2:
                logger.fatal(f"invalid register pair on line {self.line}: {self.value}", scope)

            reg1 = REGISTERS.get(regs[0].upper())
            reg2 = REGISTERS.get(regs[1].upper())

            if reg1 is None or reg2 is None:
                logger.fatal(f"unknown register on line {self.line}: {regs[0]} or {regs[1]}", scope)
            logger.verbose(f"get_integer_value: register pair {self.value} -> {reg1}, {reg2}")
            
            # insane hack to encode the register pair as a single integer
            return (reg1 & 0b00001111) << 4 | (reg2 & 0b00001111)

        elif self.type == OPERAND_TYPES["NUMBER"]:
            value = self.value.strip().lower()

            if value.startswith("0x"):
                final_value = int(value, base=16) # hex
            elif value.startswith("b"):
                final_value = int(value[1:], base=2) # binary
            elif value.isdigit():
                final_value = int(value) # decimal
            else:
                logger.fatal(f"invalid number string on line {self.line}: \"{self.value}\"", scope)

            logger.verbose(f"get_integer_value: number {self.value} -> {final_value}")
            return final_value

        elif self.type == OPERAND_TYPES["LABELNAME"]:
            label = self.value.lower()
            if label not in IRNode.labels.keys():
                logger.fatal(f"unknown label on line {self.line}: {label}", scope)
            
            logger.verbose(f"get_integer_value: label {self.value} -> {IRNode.labels[label]}")
            return IRNode.labels[label]

        logger.fatal(f"invalid operand type on line {self.line}: {self.type_string}", scope)


    def get_size(self) -> int:
        return 0


    def short_string(self) -> str:
        return f"{OPERAND_TYPE_TO_STRING[self.type]} {self.value}"


    def __str__(self):
        return f"{OPERAND_TYPE_TO_STRING[self.type]} {self.value}"


class InstructionNode(IRNode):
    """ A node representing an instruction. """

    def __init__(self, line: int, mnemonic: str, operands: list[OperandNode]):
        super().__init__(line)

        self.mnemonic = mnemonic.upper()
        self.opcode = OPCODES[self.mnemonic]
        self.operands = operands
        self.addressing_mode: int = self.get_addressing_mode()
        self.size: int = self.get_size()

    def validate_instruction_semantics(self) -> None:
        scope = "ir.py:InstructionNode.validate_instruction_semantics()"

        def assert_num_operands(required_num: int):
            scope = "ir.py:InstructionNode.assert_num_operands()"
            if len(self.operands) != required_num:
                logger.fatal(f"instruction {self.mnemonic} on line {self.line} requires {required_num} operands (got {len(self.operands)})", scope)

        def assert_operand_types(expected_types: list[list[int]]):
            scope = "ir.py:InstructionNode.assert_operand_types()"
            for i, op in enumerate[OperandNode](self.operands):
                if op.type not in expected_types[i]:
                    logger.fatal(f"{self.mnemonic} operand {i} ({op.type_string}) is not of type {', '.join([OPERAND_TYPE_TO_STRING[t] for t in expected_types[i]])} (line {self.line})", scope)

        match self.mnemonic:
            case "RET" | "IRET" | "HALT" | "NOP":
                assert_num_operands(0)
            case "POP" | "INC" | "DEC" | "NOT":
                assert_num_operands(1)
                assert_operand_types([[OPERAND_TYPES["REGISTER"]]])
            case "JMP" | "JZ" | "JNZ" | "JC" | "JNC" | "CALL" | "INT" | "PUSH":
                assert_num_operands(1)
                assert_operand_types([[OPERAND_TYPES["LABELNAME"], OPERAND_TYPES["NUMBER"]]])
            case "PUT" | "OUTB":
                assert_num_operands(2)
                assert_operand_types([[OPERAND_TYPES["LABELNAME"], OPERAND_TYPES["NUMBER"]], [OPERAND_TYPES["REGISTER"]]])
            case "GET" | "MOV" | "ADD" | "ADC" | "SUB" | "SBC" | "LSH" | "RSH" | "AND" | "OR" | "NOR" | "XOR" | "CMP" | "INB":
                assert_num_operands(2)
                assert_operand_types([[OPERAND_TYPES["REGISTER"]], [OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"]]])
            case _:
                logger.fatal(f"unknown instruction {self.mnemonic} on line {self.line}", scope)

        return


    def get_addressing_mode(self) -> int:
        """
        Get the addressing mode for an instruction.
        """
        scope = "language.py:get_addressing_mode()"

        if self.mnemonic not in OPCODES.keys():
            logger.fatal(f"unknown mnemonic on line {self.line}: {self.mnemonic}", scope)
        
        optypes = [op.type for op in self.operands]
        if not all(op_type in OPERAND_TYPES.values() for op_type in optypes):
            logger.fatal(f"invalid operands on line {self.line}: {self.operands}", scope)

        match self.mnemonic:
            # No operands
            case "RET" | "IRET" | "HALT" | "NOP":
                return ADDRESSING_MODES["NO_OPERANDS"]

            # Single register operand
            case "POP" | "INC" | "DEC" | "NOT":
                return ADDRESSING_MODES["REGISTER"]

            # single operand (either immediate or register)
            case "JMP" | "JZ" | "JNZ" | "JC" | "JNC" | "CALL" | "INT" | "PUSH":
                if optypes[0] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["IMMEDIATE"]
                else:
                    return ADDRESSING_MODES["REGISTER"]

            # two operands but the choice is made by the first operand
            case "PUT" | "OUTB":
                if optypes[0] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["REGISTER_IMMEDIATE"]
                else:
                    return ADDRESSING_MODES["REGISTER_REGISTER"]

            # two operands but the choice is made by the second operand
            case "GET" | "MOV" | "ADD" | "ADC" | "SUB" | "SBC" | "LSH" | "RSH" | "AND" | "OR" | "NOR" | "XOR" | "CMP" | "INB":
                if optypes[1] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["REGISTER_IMMEDIATE"]
                else:
                    return ADDRESSING_MODES["REGISTER_REGISTER"]

            case _:
                logger.fatal(f"{self.mnemonic} has no defined addressing mode", scope)


    def get_size(self) -> int:
        return ADDRESSING_MODE_TO_SIZE[self.addressing_mode]


    def get_bytes(self) -> bytearray:
        scope = "ir.py:InstructionNode.get_bytes()"

        logger.verbose(f"bytes: starting generation of {self.mnemonic} (line {self.line})")

        self.validate_instruction_semantics()
        binary = bytearray()

        # format for the first byte is always AAAAABBB where
        # AAAAA is the opcode and BBB is the addressing mode

        def pretty_byte_1_string(byte):
            opcode_bits = (byte >> 3) & 0b11111 # retreive opcode and mode from encoded instruction
            addressing_mode_bits = byte & 0b111
            return f"{byte:08b} | {opcode_bits:05b} ({opcode_bits}) {addressing_mode_bits:03b} ({addressing_mode_bits}) "

        logger.verbose(f"bytes: stored opcode is {self.opcode} with addressing mode {self.addressing_mode}.")

        opcode_bits = (self.opcode & 0b00011111) << 3 # mask to low 5 bits and shift three to the left
        addressing_mode_bits = self.addressing_mode & 0b00000111 # mask to low 3 bits
        byte_1 = opcode_bits | addressing_mode_bits
        binary.append(byte_1)

        logger.verbose(f"bytes: first byte is {pretty_byte_1_string(byte_1)}")

        # this is where the "simple" part ends
        # see the instruction format section in spec.md for more details on the addressing modes

        # get integer values of the operands
        operands: list[int] = [op.get_integer_value() for op in self.operands]
        logger.verbose(f"bytes: operands are {', '.join([str(val) for val in operands])}")

        def assert_operand_count(required: int):
            scope = "ir.py:InstructionNode.assert_operand_count()"
            if len(operands) != required:
                logger.fatal(f"{self.mnemonic} requires {required} operands (got {len(operands)} on line {self.line})", scope)

        def assert_immediate_size(required: int, value: int):
            scope = "ir.py:InstructionNode.assert_immediate_size()"
            if value >= (2 ** required):
                logger.fatal(f"immediate value {value} is too large for a{'n' if required == 8 else 'n'} {required}-bit immediate (line {self.line})", scope)

        match self.addressing_mode:
            case 0: # no operands, easy!
                assert_operand_count(0)
            
            case 1: # single register operand
                assert_operand_count(1)

                # the first register is encoded in the high 4 bits of the byte
                byte_2 = (operands[0] & 0b00001111) << 4
                logger.verbose(f"bytes: second byte is {byte_2:08b} (register: {operands[0]:04b})")
                binary.append(byte_2)
            
            case 2: # single 8-bit immediate operand
                
                assert_operand_count(1)
                assert_immediate_size(8, operands[0])

                # second byte is unused
                binary.append(0b00000000)
                logger.verbose(f"bytes: second byte is {0b00000000:08b} (unused)")

                # third byte is the immediate value
                byte_3 = operands[0]
                logger.verbose(f"bytes: third byte is {byte_3:08b} (imm8)")
                binary.append(byte_3)

            case 3: # two register operands
                
                assert_operand_count(2)

                # the first register is encoded in the high 4 bits of the second byte
                # and the second register is encoded in the low 4 bits
                byte_2 = (operands[0] & 0b00001111) << 4 | (operands[1] & 0b00001111)
                logger.verbose(f"bytes: second byte is {byte_2:08b} (register: {operands[0]:04b}, register: {operands[1]:04b})")
                binary.append(byte_2)

            case 4: # register and 8-bit immediate operand
                
                assert_operand_count(2)
                assert_immediate_size(8, operands[1])

                # the register is encoded in the high 4 bits of the second byte
                byte_2 = (operands[0] & 0b00001111) << 4
                logger.verbose(f"bytes: second byte is {byte_2:08b} (register: {operands[0]:04b})")
                binary.append(byte_2)

                # third byte is the immediate value
                byte_3 = operands[1]
                logger.verbose(f"bytes: third byte is {byte_3:08b} (imm8)")
                binary.append(byte_3)

            case 5: # register and 16-bit immediate operand
                
                assert_operand_count(2)
                assert_immediate_size(16, operands[1])

                # the register is encoded in the high 4 bits of the second byte
                byte_2 = (operands[0] & 0b00001111) << 4
                logger.verbose(f"bytes: second byte is {byte_2:08b} (register: {(operands[0] & 0b00001111):04b})")
                binary.append(byte_2)

                # 16-bit immediate is little endian encoded in bytes 3 and 4
                # low 8 bits of the immediate is encoded in the third byte
                byte_3 = operands[1] & 0b0000000011111111
                logger.verbose(f"bytes: third byte is {byte_3:08b} (imm16 low byte)")
                binary.append(byte_3)

                # high 8 bits of the immediate is encoded in the fourth byte
                byte_4 = operands[1] >> 8
                logger.verbose(f"bytes: fourth byte is {byte_4:08b} (imm16 high byte)")
                binary.append(byte_4)

            case 6: # register and register pair operand
                assert_operand_count(2)

                # lonely register is encoded in the high 4 bits of the second byte
                byte_2 = (operands[0] & 0b00001111) << 4
                logger.verbose(f"bytes: second byte is {byte_2:08b} (register: {(operands[0] & 0b00001111):04b})")
                binary.append(byte_2)

                # register pair is encoded in the third byte little-endian style,
                # i.e. pair A:B (L:H) is encoded as AAAABBBB

                byte_3 = operands[1] # pair is already encoded as a single integer in get_integer_value()
                logger.verbose(f"bytes: third byte is {byte_3:08b} (register pair: {operands[1] >> 4:04b}, {operands[1] & 0b00001111:04b})")
                binary.append(byte_3)

            case 7: # 16-bit immediate operand
               
                assert_operand_count(1)
                assert_immediate_size(16, operands[0])

                # byte 2 is unused
                binary.append(0b00000000)
                logger.verbose(f"bytes: second byte is {0b00000000:08b} (unused)")

                # 16-bit immediate is little endian encoded in bytes 3 and 4
                # low 8 bits if the immediate
                byte_3 = operands[0] & 0b0000000011111111
                logger.verbose(f"bytes: third byte is {byte_3:08b} (imm16 low byte)")
                binary.append(byte_3)

                # high 8 bits if the immediate
                byte_4 = operands[0] >> 8
                logger.verbose(f"bytes: fourth byte is {byte_4:08b} (imm16 high byte)")
                binary.append(byte_4)

            case _:
                logger.fatal(f"{self.mnemonic} has no defined addressing mode (line {self.line})", scope)

        logger.verbose(f"bytes: final binary: {self.pretty_bit_string(binary)}")
        return binary   


    def short_string(self) -> str:
        return f"instruction {self.mnemonic}"


    def __str__(self):
        # return f"instruction: {self.mnemonic} (line {self.line}) with {len(self.operands)} operands: {", ".join([str(op) for op in self.operands])}"
        return f"instruction {self.mnemonic} (line {self.line})"
 

class ImportDirectiveNode(IRNode):
    """ A node representing an import directive. """

    def __init__(self, line: int, filename: str):
        super().__init__(line)
        self.filename = filename

        # remove quotes from the beginning and end of the filename
        if self.filename.startswith('"') and self.filename.endswith('"'):
            self.filename = self.filename[1:-1]


    def __str__(self):
        return f"import directive: {self.filename}"


class DataDirectiveNode(IRNode):
    """ A node representing a data directive. """

    def __init__(self, line: int, data: list[tuple[str, str]]):
        super().__init__(line)

        self.data_raw = data
        self.data = self.parse_bytes()
        self.size: int = self.get_size()


    def parse_bytes(self) -> list[int]:
        scope = "ir.py:DataDirectiveNode.parse_bytes()"
        bytes: list[int] = []

        for type_string, value_string in self.data_raw:

            if type_string == "NUMBER":
                logger.verbose(f"parse_bytes: parsing number {value_string}")
                bytes.append(self.get_number_value(value_string))

            elif type_string == "STRING":
                if len(value_string) >= 2:
                    value_string = value_string[1:-1] # remove quotes
                logger.verbose(f"parse_bytes: parsing string {value_string}")
                bytes.extend(self.get_string_value(value_string))

            else:
                logger.fatal(f"invalid data type on line {self.line}: {type_string}", scope)

        return bytes


    def get_number_value(self, number_str: str) -> int:
        scope = "ir.py:DataDirectiveNode.get_number_value()"
        # turn number string into an integer (hex, binary, or decimal)

        value = number_str.strip().lower()
        if value.startswith("0x"):
            final_value = int(value, base=16) # hex
        elif value.startswith("b"):
            final_value = int(value[1:], base=2) # binary
        elif value.isdigit():
            final_value = int(value) # decimal
        else:
            logger.fatal(f"invalid number string on line {self.line}: \"{number_str}\"", scope)

        if final_value > 0xFF:
            logger.fatal(f"number {number_str} ({final_value}) is too large for an 8-bit value (line {self.line})", scope)

        logger.verbose(f"parse_bytes: \"{number_str}\" -> {final_value}")
        return final_value


    def get_string_value(self, string: str) -> list[int]:
        # get the bytes of a string
        bytes: list[int] = [ord(char) for char in string]
        logger.verbose(f"parse_bytes: got bytes of string \"{string}\": {', '.join([str(byte) for byte in bytes])}")
        return bytes


    def get_size(self) -> int:
        logger.verbose(f"data directive: got size {len(self.data)} (raw: {', '.join([str(byte) for byte in self.data])})")
        return len(self.data)


    def get_bytes(self) -> bytearray:
        bits = bytearray()
        bits.extend(self.data)
        logger.verbose(f"get_bytes: {self.pretty_bit_string(bits)} (from {self.readable_data_string()})")
        return bits


    def readable_data_string(self):
        return ", ".join([f"{value}" for _, value in self.data_raw])


    def short_string(self) -> str:
        return f"data {self.readable_data_string()}"


    def __str__(self):
        return f"data directive: {self.readable_data_string()}"


class LabelNode(IRNode):
    def __init__(self, line: int, label: str):
        super().__init__(line)
        self.label: str = label

    def __str__(self):
        return f"label: {self.label} at pc {self.pc}"


class ExpressionNode(IRNode):
    def __init__(self, line: int, expression: str):
        super().__init__(line)
        self.expression: str = expression

    def evaluate(self) -> int:
        scope = "ir.py:ExpressionNode.evaluate()"
        logger.warning(f"expression evaluation is not yet supported: skipping evaluation of {self.expression} on line {self.line}", scope)
        return 0

    def __str__(self):
        return f"expression: {self.expression}"


class MacroArgumentNode(IRNode):

    def __init__(self, line: int, name: str):
        super().__init__(line)
        self.name: str = name
        self.value: IRNode | None = None

    def __str__(self):
        return f"macro argument: {self.name}"


class MacroNode(IRNode):
    def __init__(self, line: int, name: str, args: list[MacroArgumentNode], body: list[IRNode]):
        super().__init__(line)
        self.name: str = name
        self.args: list[MacroArgumentNode] = args
        self.body: list[IRNode] = body

    def __str__(self):
        return f"macro definition: {self.name} with {len(self.args)} arguments"


class MacroCallNode(IRNode):
    def __init__(self, line: int, name: str, args: list[OperandNode]):
        super().__init__(line)
        self.name: str = name
        self.args: list[OperandNode] = args