# emulator.py
# jaide emulator
# josiah bergen, january 2026

import os
import sys
import traceback
from collections import deque
from typing import Callable

from common.isa import INSTRUCTIONS, OPCODE_FORMATS

from .constants import (
    BANK_SIZE,
    BANK_WINDOW_END,
    BANK_WINDOW_START,
    FLAG_C,
    FLAG_N,
    FLAG_O,
    FLAG_STRINGS,
    FLAG_Z,
    MEMORY_SIZE,
    MMIO_BASE,
    MMIO_END,
    MMIO_SYSTEM,
    NUM_BANKS,
    REGISTERS,
    VRAM_END,
    VRAM_SIZE,
    VRAM_START,
)
from .devices.device import Device
from .devices.disk import Disk
from .devices.graphics import Graphics
from .devices.keyboard import Keyboard
from .devices.pit import PIT
from .devices.rtc import RTC
from .exceptions import EmulatorException
from .register import Register
from .util.disasm import disassemble
from .util.logger import logger


def mask16(x: int) -> int:
    return x & 0xFFFF  # mask to 16 bits


class Emulator:
    def __init__(self, verbosity: int = logger.log_level.INFO, enabled_devices: dict[str, bool] = {}, image_file: str = ""):

        logger.set_level(verbosity)

        # general purpose registers
        self.reg: dict[str, Register] = {reg: Register(reg, 0) for reg in REGISTERS}

        # special registers
        self.pc: Register = self.reg["PC"]  # program counter
        self.sp: Register = self.reg["SP"]  # stack pointer
        self.f: Register = self.reg["F"]    # flags
        self.mb: Register = self.reg["MB"]  # memory bank

        # set stack pointer to 0xFDFF as recommended by the spec
        self.sp.set(0xFDFF)

        # memory and i/o
        self.memory: bytearray = bytearray(MEMORY_SIZE)
        self.vram: bytearray = bytearray(VRAM_SIZE)
        self.banks: list[bytearray] = [bytearray(BANK_SIZE) for _ in range(NUM_BANKS)]

        self.devices: list[Device] = []

        _no_irq = lambda _: None  # no interrupt controller; devices call this as a no-op

        # simple read/write devices
        if enabled_devices.get("pit", False): self.devices.append(PIT(_no_irq))
        if enabled_devices.get("rtc", False): self.devices.append(RTC(_no_irq))

        # graphics and keyboard devices
        if enabled_devices.get("graphics", False):
            _key_queue = deque()
            self.devices.append(Graphics(_no_irq, _key_queue, self.vram, self.shutdown))
            self.devices.append(Keyboard(_no_irq, _key_queue))

        # disk device
        if enabled_devices.get("disk", False):
            self.devices.append(Disk(_no_irq, image_file, self.read16, self.write16))

        # debugger etc.
        self.breakpoints: set[int] = set[int]()  # empty set of breakpoints
        self.halted: bool = False  # hardware halt

        # handlers keyed by mnemonic; dispatch via OPCODE_FORMATS[opcode].mnemonic
        from .handlers import handler_map
        self.handlers: dict[INSTRUCTIONS, Callable[[Emulator, tuple[int, ...]], None]] = handler_map

    # memory

    def _resolve_memory(self, addr: int) -> tuple[bytearray, int]:
        """Map a word address to (backing store, word offset within that store)."""
        if VRAM_START <= addr <= VRAM_END:
            return self.vram, addr - VRAM_START

        bank = self.mb.value % 32
        if bank != 0 and BANK_WINDOW_START <= addr <= BANK_WINDOW_END:
            return self.banks[bank - 1], addr - BANK_WINDOW_START

        return self.memory, addr

    def load_binary(self, file: str, addr: int = 0):

        # check if file exists
        if not os.path.exists(file):
            logger.error(f"file {file} does not exist.")
            return

        try:
            # read the file
            with open(file, "rb") as f:
                binary = f.read()
        except Exception as e:
            logger.error(f"error reading file {file}: {e}.")
            return

        self.memory[addr : addr + len(binary)] = binary
        logger.info(f"loaded {len(binary)} bytes to 0x{addr:04X}.")


    def read16(self, addr: int) -> int:
        # fetch a 16-bit little-endian value from memory using word addressing
        addr = mask16(addr)
        if MMIO_BASE <= addr <= MMIO_END:
            return self.mmio_read(addr)

        memory, addr = self._resolve_memory(addr)

        lo = memory[addr * 2]
        hi = memory[addr * 2 + 1]
        return (hi << 8) | lo


    def write16(self, addr: int, value: int):
        # write a 16-bit little-endian value to memory using word addressing
        addr = mask16(addr)
        if MMIO_BASE <= addr <= MMIO_END:
            self.mmio_write(addr, value)
            return

        if addr < 0x0100:  # writing to ROM (0x0000–0x00FF)
            logger.warning(f"write to ROM at 0x{addr:04X}.", "write16")
            return

        phys_addr = addr
        memory, addr = self._resolve_memory(addr)

        if addr * 2 >= len(memory):
            logger.warning(f"attempted to write to out of bounds memory (0x{phys_addr:04X}).")
            return

        bank = self.mb.value % 32
        in_bank = bank != 0 and BANK_WINDOW_START <= phys_addr <= BANK_WINDOW_END
        in_vram = VRAM_START <= phys_addr <= VRAM_END
        logger.verbose(
            f"writing 0x{value:04X} to 0x{phys_addr:04X}"
            f"{' (bank ' + str(bank) + ')' if in_bank else ''}"
            f"{' (vram)' if in_vram else ''}..."
        )

        value = mask16(value)
        memory[addr * 2] = value & 0xFF
        memory[addr * 2 + 1] = (value >> 8) & 0xFF


    # registers

    def reg_get(self, index: int) -> int:
        if index < 0 or index >= len(REGISTERS):
            raise EmulatorException(f"invalid register index {index}.")
        return self.reg[REGISTERS[index]].value


    def reg_set(self, index: int, value: int) -> None:
        if index < 0 or index >= len(REGISTERS):
            raise EmulatorException(f"invalid register index {index}.")
        self.reg[REGISTERS[index]].set(mask16(value))

    # flag helpers
    def flag_get(self, bit: int) -> bool:
        if bit < 0 or bit > 4:
            raise EmulatorException(f"attempted to get invalid flag bit {bit}.")
        return (self.f.value >> bit) & 1 == 1


    def flag_set(self, bit: int, value: bool) -> None:
        if bit < 0 or bit > 4:
            raise EmulatorException(f"attempted to set invalid flag bit {bit}.")
        bit_mask = 1 << bit
        # reset the flag bit, then set it if needed
        self.f.set((self.f.value & ~bit_mask) | ((1 if value else 0) << bit))


    def set_all_flags(self, z: int, c: int, n: int, o: int) -> None:
        self.flag_set(FLAG_Z, bool(z))
        self.flag_set(FLAG_C, bool(c))
        self.flag_set(FLAG_N, bool(n))
        self.flag_set(FLAG_O, bool(o))

    # MMIO helpers (0xFE00–0xFEFF, bank-independent)

    def mmio_read(self, addr: int) -> int:
        for device in self.devices:
            if addr in device.read_dispatch:
                return device.mmio_read(addr)

        logger.warning(f"no device at MMIO 0x{addr:04X}, read is undefined.")
        return 0

    def mmio_write(self, addr: int, value: int) -> None:
        value = mask16(value)

        if addr == MMIO_SYSTEM:
            logger.debug(f"system MMIO write: 0x{value:04X} -> 0x{addr:04X}")
            match value:
                case 0x01:  # reset
                    self.reset()
                case 0x02:  # halt
                    self.halted = True
                case 0x03:  # power off
                    self.shutdown()
                case _:
                    pass

        for device in self.devices:
            if addr in device.write_dispatch:
                device.mmio_write(addr, value)
                break

    def reset(self) -> None:
        self.__init__()
        logger.info("emulator reset")


    def shutdown(self) -> None:
        print("shutting down...")
        sys.exit(0)

    # main fetch/decode

    def fetch(self) -> int:
        # fetch word and increment program counter
        value = self.read16(self.pc.value)
        self.pc.set(self.pc.value + 1)
        return value


    def decode(self) -> tuple[int, ...]:
        word = self.fetch()
        regs, instr = word & 0xFF, (word >> 8) & 0xFF

        opcode = instr  # flat 8-bit opcode
        reg_a = (regs >> 4) & 0xF  # ssss/high nibble
        reg_b = regs & 0xF  # dddd/low nibble

        if opcode not in OPCODE_FORMATS:
            raise EmulatorException(f"invalid opcode 0x{opcode:02x} at 0x{self.pc.value:04x}.")

        fmt = OPCODE_FORMATS[opcode]
        imm16 = self.fetch() if fmt.imm_operand is not None else 0

        return opcode, reg_a, reg_b, imm16

    # main run loop

    def run(self) -> None:

        try:
            while True:
                # normal execution
                self.step()
        except EmulatorException as e:
            # we enter exceptional control flow either if something went wrong,
            # or if the user interrupts the program
            logger.error(f"emulator stopped: {e.message}")
        except KeyboardInterrupt:
            # prevent ctrl+c from bubbling up to the __main__() function,
            # allowing easy program interruption, etc. while allowing the repl to persist
            print("! execution stopped (user interrupt).")
        except Exception as e:
            # general exception. this is an emulator code error, 
            # not an assembly error. allow the repl to persist.
            logger.error(f"fatal! while running instruction at 0x{(self.pc.value)}:\n{traceback.format_exc()}")


    def step(self) -> None:

        # hardware-level overrides
        if self.halted:
            raise EmulatorException("halted")
        if self.pc.value in self.breakpoints:
            raise EmulatorException(f"hit breakpoint at {self.pc}")

        # tick all devices
        for device in self.devices:
            device.tick()

        # normal fetch/decode/execute
        decoded = self.decode()
        opcode = decoded[0]

        logger.verbose(
            f"{disassemble(decoded):<13}"
            f'{" ".join([f"{r}: {self.reg[r].value:0>4X} " if len(f"{self.reg[r].value:X}") >= 4 else f"{r}: {self.reg[r].value:X}{' ' * (4 - len(f'{self.reg[r].value:X}'))} " for r in self.reg if r != "F"])} '
            f"{" ".join([f"{FLAG_STRINGS[i]}" if self.flag_get(i) else "-" for i in FLAG_STRINGS])}"
        )

        self.handlers[OPCODE_FORMATS[opcode].mnemonic](self, decoded)

    # core helpers

    @staticmethod
    def _signed16(x: int) -> int:
        """Interpret a 16-bit unsigned value as a signed integer."""
        return x if x < 0x8000 else x - 0x10000


    def _add_core(self, a: int, b: int, carry_in: int = 0) -> int:
        full = a + b + carry_in
        result = mask16(full)
        carry = 1 if full > 0xFFFF else 0
        overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
        self.set_all_flags(result == 0, carry, result & 0x8000 != 0, overflow)
        return result


    def _sub_core(self, a: int, b: int, borrow_in: int = 0) -> int:
        full = a - b - borrow_in
        result = mask16(full)
        carry = 1 if a >= b + borrow_in else 0
        overflow = 1 if (((a ^ b) & 0x80) != 0 and ((a ^ result) & 0x80) != 0) else 0
        self.set_all_flags(result == 0, carry, result & 0x8000 != 0, overflow)
        return result


    def _lsh_core(self, a: int, b: int) -> int:
        # TODO: test
        full = a << b
        result = mask16(full)
        carry = 1 if a & (1 << (16 - b)) else 0
        overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
        self.set_all_flags(result == 0, carry, result < 0, overflow)
        return result


    def _rsh_core(self, a: int, b: int) -> int:
        # TODO: test
        full = a >> b
        result = mask16(full)
        carry = 1 if a & (1 << (b - 1)) else 0
        overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
        self.set_all_flags(result == 0, carry, result < 0, overflow)
        return result


    def _asr_core(self, a: int, b: int) -> int:
        carry = 1 if b > 0 and (a >> (b - 1)) & 1 else 0
        result = mask16(self._signed16(a) >> b)
        self.set_all_flags(result == 0, carry, result & 0x8000 != 0, 0)
        return result


    def _push_core(self, value: int) -> None:
        # decrement sp (put pointer into location of new value)
        self.sp.set(self.sp.value - 1)
        self.write16(self.sp.value, value)


    def _pop_core(self) -> int:
        value = self.read16(self.sp.value)  # read value from stack
        self.sp.set(self.sp.value + 1)  # increment stack pointer
        self.flag_set(FLAG_Z, value == 0)
        return value


