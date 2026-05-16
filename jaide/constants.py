# constants.py
# emulator-specific constants for the jaide project.
# josiah bergen, january 2026

# ISA definitions are in common/isa.py — import from there, not here.
from common.isa import OPCODE_FORMATS

MEMORY_SIZE = 0x10000 * 2  # 128KiB total (64K word addresses × 2 bytes)
BANK_SIZE   = 0x4100 * 2   # bytes for the 0xBC00–0xFCFF banked window (0x4100 word addresses)
NUM_BANKS   = 31           # 32 banks total, bank 0 is built-in RAM

BANK_WINDOW_START = 0xBC00
BANK_WINDOW_END   = 0xFCFF

MMIO_BASE = 0xFE00
MMIO_END  = 0xFEFF
MMIO_SYSTEM = 0xFEFF

# Register names in index order (matches REGISTERS enum in common.isa)
REGISTERS = ["A", "B", "C", "D", "E", "X", "Y", "Z", "F", "MB", "SP", "PC"]

FLAG_C = 0  # carry
FLAG_Z = 1  # zero
FLAG_N = 2  # negative
FLAG_O = 3  # overflow
FLAG_I = 4  # interrupts enabled

FLAG_STRINGS: dict[int, str] = {
    FLAG_C: "C",
    FLAG_Z: "Z",
    FLAG_N: "N",
    FLAG_O: "O",
    FLAG_I: "I",
}

# Human-readable mnemonic strings (for logging / disassembly)
MNEMONICS: dict[int, str] = {
    opcode: fmt.mnemonic.name
    for opcode, fmt in OPCODE_FORMATS.items()
}
