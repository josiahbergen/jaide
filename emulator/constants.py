# constants.py
# emulator-specific constants for the jaide project.
# josiah bergen, january 2026

from common.isa import OPCODE_FORMATS

MEMORY_SIZE = 0x10000 * 2  # 128KiB total (64K word addresses × 2 bytes)
BANK_SIZE   = 0x4000 * 2   # bytes per bank (0x4000 = 16384 words, 2¹⁴)
NUM_BANKS   = 31           # MB=1..31 map to banks[0..30] for user processes

ROM_END  = 0x00FF
ROM_SIZE = 0x0100 * 2  # 256 words, enough for a simple bootloader

BANK_WINDOW_START = 0x7000
BANK_WINDOW_END   = 0xAFFF

VRAM_START = 0x4000
VRAM_END   = 0x4FFF
VRAM_SIZE  = 0x1000 * 2  # 4096 words (8 KiB)

MMIO_BASE = 0xFE00
MMIO_END  = 0xFEFF
MMIO_SYSTEM = 0xFEFF

# Register names in index order (matches REGISTERS enum in common.isa)
REGISTERS = ["A", "B", "C", "D", "E", "X", "Y", "Z", "F", "MB", "SP", "PC"]

FLAG_C = 0  # carry
FLAG_Z = 1  # zero
FLAG_N = 2  # negative
FLAG_O = 3  # overflow

FLAG_STRINGS: dict[int, str] = {
    FLAG_C: "C",
    FLAG_Z: "Z",
    FLAG_N: "N",
    FLAG_O: "O",
}

# Human-readable mnemonic strings (for logging / disassembly)
MNEMONICS: dict[int, str] = {
    opcode: fmt.mnemonic.name
    for opcode, fmt in OPCODE_FORMATS.items()
}
