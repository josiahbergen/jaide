# constants.py
# emulator-specific constants for the jaide project.
# josiah bergen, january 2026

# ISA definitions are in common/isa.py — import from there, not here.
from common.isa import INSTRUCTIONS, MODES, OPCODE_FORMATS, InstructionFormat

MEMORY_SIZE = 0x1FFFF + 1  # 128KiB, word addressable
BANK_SIZE   = 0x4000       # 32KiB,  word addressable
NUM_BANKS   = 31           # 32 banks total, bank 0 is built-in RAM

# Register names in index order (matches REGISTERS enum in common.isa)
REGISTERS = ["A", "B", "C", "D", "E", "X", "Y", "Z", "F", "MB", "SP", "PC"]

FLAG_C = 0  # carry
FLAG_Z = 1  # zero
FLAG_N = 2  # negative
FLAG_O = 3  # overflow
FLAG_I = 4  # interrupts enabled

# Human-readable mnemonic strings (for logging / disassembly)
MNEMONICS: dict[int, str] = {
    opcode: fmt.mnemonic.name
    for opcode, fmt in OPCODE_FORMATS.items()
}
