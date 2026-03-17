# language/ir.py
# intermediate representation for the JASM language.
# josiah bergen, december 2025

import os
import copy
from enum import IntEnum

from ...util.logger import logger
from ...language.isa import INSTRUCTIONS, MODES, OPCODE_MAP


class IRNode:
    """ Super simple base node class for the IR. """
    
    def __init__(self, line: int):
        self.line: int = line
        self.pc: int = 0 # where the instruction will be placed in the binary

    def __str__(self) -> str:
        scope = "ir.py:IRNode.__str__()"
        logger.warning(f"__str__() not implemented for {type(self)}", scope)
        return f"{type(self).__name__} at line {self.line}"

    # semantic methods (only defined by some nodes, not all)

    def get_size(self) -> int:
        scope = "ir.py:IRNode.get_size()"
        logger.fatal(f"get_size() not implemented for {type(self).__name__} on line {self.line}", scope)

# top-level nodes

class Operand(IRNode):
    # base operand class. all operands inherit from this.
    # useful for type hinting.
    def __init__(self, line: int, mode: MODES):
        super().__init__(line)
        self.mode: MODES = mode # the addressing mode of the operand

    def get_value(self) -> int:
        scope = "ir.py:Operand.get_value()"
        logger.fatal(f"get_value() not implemented for {type(self).__name__} on line {self.line}", scope)


class InstructionNode(IRNode):
    """ A node representing an instruction. """

    def __init__(self, line: int, mnemonic: str, operands: list[Operand]):
        super().__init__(line)

        self.mnemonic: INSTRUCTIONS = INSTRUCTIONS[mnemonic.upper()]
        self.operands: list[Operand] = operands

        # these gotta wait until after macro expansion
        self.opcode: int = 0
        self.size: int = 0
 
    def __str__(self) -> str:
        return f"{self.mnemonic.name} {', '.join([str(op) for op in self.operands])}"

    def get_opcode(self) -> int:
        try:
            # yeah bro readable code is a priorty trust me bro
            return OPCODE_MAP[(self.mnemonic, tuple[MODES, ...](operand.mode for operand in self.operands))]
        except KeyError:
            key = (self.mnemonic, tuple[MODES, ...](operand.mode for operand in self.operands))
            logger.fatal(f"invalid opcode for {self.mnemonic.name} with key {key} (line {self.line})", "ir.py:InstructionNode.get_opcode()")
    
    def get_size(self) -> int:
        # size in words!
        if any((operand.mode in [MODES.IMM, MODES.RELATIVE, MODES.OFF_POINTER, MODES.REL_POINTER] for operand in self.operands)):
            return 2
        return 1 # also catches instructions with no operands


class LabelNode(IRNode):

    def __init__(self, line: int, name: str):
        super().__init__(line)
        self.name: str = name

    def __str__(self) -> str:
        return f"{self.name}:"

    def get_size(self) -> int:
        return 0


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
        return f"import \"{self.filename}\""


class DataDirectiveNode(IRNode):

    class Type(IntEnum):
        NUMBER = 0
        STRING = 1

    def __init__(self, line: int, items: list[tuple[Type, str]]):
        super().__init__(line)
        self.items: list[tuple[DataDirectiveNode.Type, str]] = items
        self.data: list[int] = self.parse_bytes()
        self.size: int = self.get_size()

    def __str__(self) -> str:
        strs = [f"{d[1]}" if d[0] == self.Type.NUMBER else f'"{d[1]}"' for d in self.items]
        return f"data {', '.join(strs)}"

    def parse_bytes(self) -> list[int]:
        bytes: list[int] = []
        logger.verbose(f"parse_bytes: parsing {len(self.items)} items")
        for type, value in self.items:
            if type == self.Type.NUMBER:
                bytes.append(self.parse_number(value))
            else:
                bytes.extend(self.parse_string(value))
        return bytes

    def parse_number(self, string: str) -> int:
        scope = "ir.py:DataDirectiveNode.get_number_value()"
        value = int(string, 0)
        
        if value < -32768 or value > 0xFFFF:
            logger.fatal(f"number {string} ({value}) out of range for a 16-bit value (line {self.line})", scope)
        
        if value < 0:
            value = value & 0xFFFF
        
        logger.verbose(f"parse_bytes: {string} -> {value}")
        return value


    def parse_string(self, string: str) -> list[int]:
        bytes: list[int] = [ord(char) for char in string]
        logger.verbose(f"parse_bytes: got bytes of string \"{string}\": {', '.join([str(byte) for byte in bytes])}")
        return bytes

    def get_size(self) -> int:
        logger.verbose(f"data directive: got size {len(self.data)} (raw: {', '.join([str(byte) for byte in self.data])})")
        return len(self.data)

    def encode(self) -> bytearray:
        bits = bytearray()
        for word in self.data:
            bits.append(word & 0xFF)
            bits.append((word >> 8) & 0xFF)
        logger.verbose(f"get_bytes: {" ".join([f'{byte:04X}' for byte in bits])[:100]}... ({len(bits)} bytes from {', '.join([f'{d[1]}' for d in self.items])})")
        return bits


class MacroDefinitionNode(IRNode):

    def __init__(self, line: int, name: str, args: list[str], body: list[IRNode]):
        super().__init__(line)
        self.name: str = name.upper() # macro name
        self.placeholders: list[str] = args # placeholder identifiers for the arguments
        self.body: list[IRNode] = body


    def __str__(self) -> str:
        return f"macro def {self.name} {', '.join(self.placeholders)} ({len(self.body)} body nodes)"


    def expand(self, args_to_insert: list[Operand], line_of_call: int) -> list[IRNode]:
        scope = "ir.py:MacroDefinitionNode.expand()"
        from jasm.language.ir.operands import MacroArgumentOperand

        # map the placeholder names to the actual arguments
        placeholder_to_value: dict[str, Operand] = {
            placeholder: args_to_insert[i] for i, placeholder in enumerate[str](self.placeholders)
        }
        logger.verbose(f"macro: argument map: {', '.join([f"{k}: {v}" for k, v in placeholder_to_value.items()])}")

        # use a deep copy of the body to avoid poisoning the original macro definition
        template: list[IRNode] = copy.deepcopy(self.body)
        for element in template:

            if isinstance(element, MacroCallNode):
                # this would involve finding and expanding the def, but that's a lot of work for now
                # we would have to think about how macro args can be put in the call for another macro, etc.
                logger.fatal(f"nested macro calls are not yet supported: {self.name} (line {line_of_call})", scope)

            elif isinstance(element, DataDirectiveNode):
                # this won't crash, but it's probably not a good idea
                logger.warning(f"macro contains data directive: {self.name} why are you doing this? (line {line_of_call})", scope)

            elif isinstance(element, LabelNode):
                # mangle the label name and all its references in the macro's scope
                self._mangle_label(template, element, line_of_call)

            elif isinstance(element, InstructionNode):
                # replace macro arguments with actual values
                for i, operand in enumerate[Operand](element.operands):
                    if isinstance(operand, MacroArgumentOperand):
                        logger.verbose(f"macro: replacing macro argument {operand.placeholder} with {placeholder_to_value[operand.placeholder]}")
                        element.operands[i] = placeholder_to_value[operand.placeholder]
            
            else:
                logger.fatal(f"macros can only contain instructions: {self.name} (line {line_of_call})", scope)
        
        # done processing this invocation, return the modified nodes
        return template


    def _mangle_label(self, template: list[IRNode], label: LabelNode, line_of_call: int) -> None:
        from jasm.language.ir.operands import LabelOperand
        old_name = label.name
        new_label = f"{old_name}__{self.name}__{line_of_call}"

        # find and update all operands in all instructions that reference the old label
        references = 0
        instructions = [element for element in template if isinstance(element, InstructionNode)]
        for instruction in instructions:
            labels_to_change = [op for op in instruction.operands if isinstance(op, LabelOperand) and op.name == old_name]
            for l in labels_to_change:
                l.name = new_label
                references += 1

        logger.verbose(f"macro: mangled label {old_name} and {references} references to {new_label} on line {line_of_call}")


class MacroCallNode(IRNode):

    def __init__(self, line: int, name: str, args: list[Operand]):
        super().__init__(line)
        self.name: str = name.upper() # macro being called
        self.args: list[Operand] = args # real values to substitute for the placeholders

    def __str__(self) -> str:
        return f"macro call: {self.name} with {', '.join([str(op) for op in self.args])}"


class ExpressionNode(IRNode):
    def __init__(self, line: int, expression: str):
        super().__init__(line)
        self.expression: str = expression

    def __str__(self) -> str:
        return f"expression: {self.expression}"