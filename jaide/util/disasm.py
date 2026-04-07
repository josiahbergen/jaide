from common.isa import OPCODE_FORMATS
from jaide.constants import REGISTERS

def disassemble(decoded: tuple[int, ...]) -> str:

    opcode, reg_a, reg_b, imm16 = decoded
    
    if opcode not in OPCODE_FORMATS:
        return f"??? (unknown opcode 0x{opcode:02x})"

    fmt = OPCODE_FORMATS[opcode]

    reg_a_str = f" {REGISTERS[reg_a]}" if fmt.src_operand is not None else ""
    reg_b_str = f" {REGISTERS[reg_b]}" if fmt.dest_operand is not None else ""
    imm16_str = f" {imm16:04X}" if fmt.imm_operand is not None else ""

    return f"{fmt.mnemonic.name}{reg_a_str}{reg_b_str}{imm16_str}"
