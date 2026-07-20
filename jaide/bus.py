from typing import Callable

from .constants import (
    BANK_SIZE,
    BANK_WINDOW_END,
    BANK_WINDOW_START,
    MEMORY_SIZE,
    MMIO_BASE,
    MMIO_END,
    NUM_BANKS,
    ROM_END,
    ROM_SIZE,
    VRAM_END,
    VRAM_SIZE,
    VRAM_START,
)
from .util.logger import logger


class MemoryBus:
    
    def __init__(self, get_selected_bank: Callable[[], int],mmio_read:  Callable[[int], int], mmio_write: Callable[[int, int], None]):
        # functions supplied by the cpu/devices
        self.get_selected_bank = get_selected_bank
        self.mmio_read = mmio_read
        self.mmio_write = mmio_write
        # initialize bytearrays for main memory, vram, and banks
        self.memory = bytearray(MEMORY_SIZE)
        self.vram = bytearray(VRAM_SIZE)
        self.banks = [bytearray(BANK_SIZE) for _ in range(NUM_BANKS)]

    @property
    def vram_view(self) -> memoryview:
        # read-only reference to vram
        return memoryview(self.vram).toreadonly()

    def read16(self, address: int, *, bank: int | None = None) -> int:
        # read and return 16-bit word from memory, dispatching to mmio_read if necessary. 
        address &= 0xFFFF # mask address to 16 bits
        
        if MMIO_BASE <= address <= MMIO_END:
            # if read is from mmio, dispatch to mmio_read
            return self.mmio_read(address) & 0xFFFF

        # resolve storage and contstruct word
        storage, offset = self.resolve_storage(address, bank)
        return storage[offset] | (storage[offset + 1] << 8)

    def write16(self, address: int, value: int, *, bank: int | None = None) -> None:
        # write 16-bit word to memory, dispatching to mmio_write if necessary.
        address, value = address & 0xFFFF, value & 0xFFFF # mask address and value to 16 bits

        if MMIO_BASE <= address <= MMIO_END:
            # if write is to mmio, dispatch to mmio_write
            self.mmio_write(address, value)
            return  # mmio_write does not return a value

        if address <= ROM_END:
            # attempting to write to rom... oh no!
            logger.warning(f"write to ROM at 0x{address:04X}.", "MemoryBus.write16")
            return

        # write word to storage and return
        storage, offset = self.resolve_storage(address, bank)
        storage[offset] = value & 0xFF
        storage[offset + 1] = value >> 8

    def peek16(self, address: int, *, bank: int | None = None) -> int:
        # DEBUG FUNCTION:read 16-bit word WITHOUT triggering mmio side effects.
        # not implemented in hardware, used only for debugging.
        if MMIO_BASE <= address <= MMIO_END:
            return 0 # reading from mmio, exit early

        # not reading from mmio, so read as normal.
        return self.read16(address, bank=bank)

    def load_bytes(self, address: int, data: bytes, *, bank: int | None = None) -> None:
        # DEBUG FUNCTION: directly load words to memory, bypassing rom protection and mmio dispatching.
        # not implemented in hardware, used only for debugging.
        if len(data) % 2:
            raise ValueError("binary data must contain a whole number of 16-bit words")

        for byte in range(0, len(data), 2):
            # parse word address and assemble little-endian word from its two bytes
            value = data[byte] | (data[byte + 1] << 8)
            word_address = (address + byte // 2) & 0xFFFF

            if MMIO_BASE <= word_address <= MMIO_END:
                # skip mmio, but don't crash.
                logger.warning(f"unable to load binary data into MMIO at 0x{word_address:04X}.", "MemoryBus.load_bytes")
                continue

            # write word to storage
            storage, offset = self.resolve_storage(word_address, bank)
            storage[offset] = value & 0xFF
            storage[offset + 1] = value >> 8

    def reset(self) -> None:
        # reset memory, vram, and banks. protects rom.
        self.memory[ROM_SIZE:] = bytes(MEMORY_SIZE - ROM_SIZE)
        self.vram[:] = bytes(VRAM_SIZE)
        self.banks = [bytearray(BANK_SIZE) for _ in range(NUM_BANKS)]

    def resolve_storage(self, address: int, bank: int | None) -> tuple[bytearray, int]:
        # gets the storage (bytearray) and the byte offset (int) for the
        # word at address. abstraction layer for the different bytearrays 
        # in which memory is stored (vram and banks).

        if VRAM_START <= address <= VRAM_END:
            # if address is in vram, use vram view and resolve
            return self.vram, (address - VRAM_START) * 2

        # memory bank register effectively overflows after NUM_BANKS
        # TODO: is this documented, or accurate?
        selected_bank = self.get_selected_bank() if bank is None else bank
        selected_bank %= (NUM_BANKS + 1)

        if selected_bank and BANK_WINDOW_START <= address <= BANK_WINDOW_END:
            # we are using banked memory, resolve the address from the selected bank
            return self.banks[selected_bank - 1], (address - BANK_WINDOW_START) * 2

        # base case; use main memory
        return self.memory, (address) * 2
