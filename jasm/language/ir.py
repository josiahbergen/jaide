# language/ir.py
# intermediate representation for the JASM language.
# josiah bergen, december 2025

from .constants import ( 
    OPCODES, 
    OPERAND_TYPES, 
    OPERAND_TYPE_TO_STRING, 
    REGISTERS, 
    ADDRESSING_MODES, 
    ADDRESSING_MODE_TO_SIZE, 
    ADDRESSING_MODE_TO_STRING, 
    INSTRUCTION_ENCODINGS, 
    LOC
)
from ..util.logger import logger


class IRNode:
    """ Really simple base node class for the IR. """
    
    # class variable to store resolved labels
    labels: dict[str, int] = {}
    # class variable to store macro definitions
    macros: dict[str, 'MacroNode'] = {}

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
        self.addressing_mode: int | None = None
        self.size: int | None = None

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
            # No operands
            case "HALT" | "NOP" | "RET" | "IRET":
                assert_num_operands(0)

            # RA
            case "POP" | "INC" | "DEC" | "NOT":
                assert_num_operands(1)
                assert_operand_types([[OPERAND_TYPES["REGISTER"]]])

            # RA/IMM8 and [IMM16]/[RA]
            case "PUSH" | "CALL" | "INT" | "JMP" | "JZ" | "JNZ" | "JC" | "JNC":
                assert_num_operands(1)
                assert_operand_types([[OPERAND_TYPES["NUMBER"], OPERAND_TYPES["REGISTER"], OPERAND_TYPES["LABELNAME"]]])

            # RA/IMM16, RB and [RA]/[IMM16], RB
            case "OUTB" | "PUT":
                assert_num_operands(2)
                assert_operand_types([[OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"], OPERAND_TYPES["LABELNAME"]], [OPERAND_TYPES["REGISTER"]]])

            # RA, RB/IMM16 and RA, [RB]/[IMM16]
            case "MOV" | "ADD" | "ADC" | "SUB" | "SBC" | "LSH" | "RSH" | "AND" | "OR" | "NOR" | "XOR" | "INB" | "CMP" | "GET":
                assert_num_operands(2)
                assert_operand_types([[OPERAND_TYPES["REGISTER"]], [OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"], OPERAND_TYPES["LABELNAME"]]])

            case _:
                logger.fatal(f"unknown instruction {self.mnemonic} on line {self.line}", scope)


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
                return ADDRESSING_MODES["NULL"]

            # RA
            case "POP" | "INC" | "DEC" | "NOT":
                return ADDRESSING_MODES["REGISTER"]

            # RA/IMM8
            case "PUSH" | "INT":
                if optypes[0] == OPERAND_TYPES["REGISTER"]:
                    return ADDRESSING_MODES["REGISTER"]
                else:
                    return ADDRESSING_MODES["IMMEDIATE"]

            case "CALL":
                if optypes[0] == OPERAND_TYPES["REGISTER"]:
                    return ADDRESSING_MODES["REGISTER_ADDRESS"]
                else:
                    return ADDRESSING_MODES["IMMEDIATE_ADDRESS"]


            # [IMM16]/[RA]
            case "JMP" | "JZ" | "JNZ" | "JC" | "JNC":
                if optypes[0] == OPERAND_TYPES["REGISTER"]:
                    return ADDRESSING_MODES["REGISTER_ADDRESS"]
                else:
                    return ADDRESSING_MODES["IMMEDIATE_ADDRESS"]

            # RA/IMM16, RB
            case "OUTB":
                if optypes[0] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["IMMEDIATE"]
                else:
                    return ADDRESSING_MODES["REGISTER"]

            # RA, RB/IMM16
            case "MOV" | "ADD" | "ADC" | "SUB" | "SBC" | "LSH" | "RSH" | "AND" | "OR" | "NOR" | "XOR" | "INB" | "CMP":
                logger.verbose(f"get_addressing_mode: optypes[1] is {optypes[1]}")
                if optypes[1] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["IMMEDIATE"]
                else:
                    return ADDRESSING_MODES["REGISTER"]

            # [RA]/[IMM16], RB
            case "PUT":
                if optypes[0] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["IMMEDIATE_ADDRESS"]
                else:
                    return ADDRESSING_MODES["REGISTER_ADDRESS"]

            # RA, [RB]/[IMM16]
            case "GET":
                if optypes[1] == OPERAND_TYPES["NUMBER"]:
                    return ADDRESSING_MODES["IMMEDIATE_ADDRESS"]
                else:
                    return ADDRESSING_MODES["REGISTER_ADDRESS"]

            case _:
                logger.fatal(f"{self.mnemonic} has no defined addressing mode", scope)


    def get_size(self) -> int:
        scope = "ir.py:InstructionNode.get_size()"
        if self.addressing_mode is None:
            logger.fatal(f"instruction {self.mnemonic} on line {self.line} has no addressing mode", scope)
        return ADDRESSING_MODE_TO_SIZE[self.addressing_mode]


    def get_bytes(self) -> bytearray:
        scope = "ir.py:InstructionNode.get_bytes()"

        logger.verbose(f"bytes: starting generation of {self.mnemonic} {" ".join([op.value for op in self.operands])} (line {self.line})")

        self.validate_instruction_semantics()
        
        if self.addressing_mode is None:
            logger.fatal(f"instruction {self.mnemonic} on line {self.line} has no addressing mode", scope)
        if self.size is None:
            logger.fatal(f"instruction {self.mnemonic} on line {self.line} has no size", scope)

        binary = bytearray()

        # format for the first byte is always AAAAABBB where
        # AAAAA is the opcode and BBB is the addressing mode

        def pretty_byte_1_string(byte):
            opcode_bits = (byte >> 2) & 0b111111 # retreive opcode and mode from encoded instruction
            addressing_mode_bits = byte & 0b11
            return f"{byte:08b} | {opcode_bits:06b} ({opcode_bits}) {addressing_mode_bits:02b} ({addressing_mode_bits}) "

        logger.verbose(f"bytes: stored opcode is {self.opcode} with addressing mode {ADDRESSING_MODE_TO_STRING[self.addressing_mode]}.")

        opcode_bits = (self.opcode & 0b00111111) << 2 # mask to low 6 bits and shift two to the left
        addressing_mode_bits = (0 if (self.addressing_mode == -1) else self.addressing_mode) & 0b00000011 # mask to low 2 bits
        byte_1 = opcode_bits | addressing_mode_bits

        logger.verbose(f"bytes: first byte is {pretty_byte_1_string(byte_1)}")

        # this is where the "simple" part ends
        # see the instruction format section in spec.md for more details on the addressing modes

        # get integer values of the operands
        operands: list[int] = [op.get_integer_value() for op in self.operands]
        logger.verbose(f"bytes: operands are {', '.join([str(val) for val in operands])}")

        def assert_bit_length(required: int, value: int):
            scope = "ir.py:InstructionNode.assert_bit_length()"
            if value >= (2 ** required):
                logger.fatal(f"immediate value {value} is too large for a{'n' if required == 8 else 'n'} {required}-bit immediate (line {self.line})", scope)

        # if this instruction/addressing mode pair expects a value for ra, add it to the binary
        encoding = INSTRUCTION_ENCODINGS[self.mnemonic][self.addressing_mode]
        logger.verbose(f"bytes: encoding is {", ".join([f"{k}: {v}" for k, v in encoding.items()])}")

        rega_bits = operands[encoding[LOC.REGA].value] if encoding[LOC.REGA] is not None else 0
        regb_bits = operands[encoding[LOC.REGB].value] if encoding[LOC.REGB] is not None else 0
        imm16_bits = operands[encoding[LOC.IMM16].value] if encoding[LOC.IMM16] is not None else None

        assert_bit_length(4, rega_bits)
        assert_bit_length(4, regb_bits)

        reg_byte = (rega_bits << 4) | regb_bits
        logger.verbose(f"bytes: reg byte is {pretty_byte_1_string(reg_byte)}")

        # its gotta be little endian, so the reg byte goes first
        binary.append(reg_byte)
        binary.append(byte_1)


        if imm16_bits is not None:
            assert_bit_length(16, imm16_bits)
            imm16_bytes = imm16_bits.to_bytes(2, byteorder="little")
            binary.extend(imm16_bytes)
            logger.verbose(f"bytes: imm16 bytes are {self.pretty_bit_string(imm16_bytes)}")

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

        if final_value > 0xFFFF:
            logger.fatal(f"number {number_str} ({final_value}) is too large for a 16-bit value (line {self.line})", scope)

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
        for word in self.data:
            bits.append(word & 0xFF)
            bits.append((word >> 8) & 0xFF)
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


class MacroCallNode(IRNode):
    def __init__(self, line: int, name: str, args: list[OperandNode]):
        super().__init__(line)
        self.name: str = name
        self.args: list[OperandNode] = args

    def __str__(self):
        return f"macro call to {self.name} with {len(self.args)} arguments"


class MacroArgumentNode(IRNode):

    def __init__(self, line: int, name: str, index: int):
        super().__init__(line)
        self.name: str = name
        self.value: IRNode | None = None
        self.index: int = index

    def __str__(self):
        return f"macro argument: {self.name} (index {self.index})"


class MacroNode(IRNode):
    def __init__(self, line: int, name: str, args: list[MacroArgumentNode], body: list[IRNode]):
        super().__init__(line)
        self.name: str = name
        self.args: list[MacroArgumentNode] = args
        self.body: list[IRNode] = body

    def expand(self, real_args: list[OperandNode]) -> list[IRNode]:
        scope = "ir.py:MacroNode.expand()"

        args_map: dict[str, OperandNode] = {}
        for arg in self.args:
            args_map[arg.name] = real_args[arg.index]
        logger.verbose(f"macro: args map: {', '.join([f"{k}: {v}" for k, v in args_map.items()])}")

        for instr in self.body:

            # error checking
            if isinstance(instr, MacroCallNode):
                logger.fatal(f"macros cannot contain macro calls: {self.name} (line {self.line})", scope)
            elif isinstance(instr, DataDirectiveNode):
                logger.fatal(f"macros cannot contain data directives: {self.name} (line {self.line})", scope)
            elif isinstance(instr, LabelNode):
                logger.fatal(f"macros cannot contain labels: {self.name} (line {self.line})", scope)
            elif not isinstance(instr, InstructionNode):
                logger.fatal(f"macros can only contain instructions: {self.name} (line {self.line})", scope)

            for i, operand in enumerate[OperandNode](instr.operands):
                if operand.type == OPERAND_TYPES["MACRO_ARG"]:
                    logger.verbose(f"macro: replacing macro argument {operand.value} with {args_map[operand.value]}")
                    instr.operands[i] = args_map[operand.value]
            

        return self.body

    def __str__(self):
        return f"macro definition {self.name} with {len(self.args)} arguments"

