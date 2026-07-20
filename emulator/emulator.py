# emulator.py
# jaide emulator
# josiah bergen, january 2026

import os
import sys
import time
import traceback
from collections import deque
from typing import Callable

from common.isa import INSTRUCTIONS, OPCODE_FORMATS

from .bus import MemoryBus
from .constants import (
    FLAG_C,
    FLAG_N,
    FLAG_O,
    FLAG_STRINGS,
    FLAG_Z,
    MMIO_SYSTEM,
    REGISTERS,
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


def mask16(value: int) -> int:
     # mask value to 16 bits
    return value & 0xFFFF


class Emulator:
    def __init__(self, verbosity: int = logger.log_level.INFO, enabled_devices: dict[str, bool] = {}, image_file: str = ""):
        logger.set_level(verbosity)

        # registers
        self.reg: dict[str, Register] = {reg: Register(reg, 0) for reg in REGISTERS}
        self.pc = self.reg["PC"]  # program counter
        self.sp = self.reg["SP"]  # stack pointer
        self.f  = self.reg["F"]   # flags
        self.mb = self.reg["MB"]  # memory bank

        # set stack pointer to 0xfdff as recommended by the spec
        self.sp.set(0xfdff)

        # memory bus and devices
        self.bus = MemoryBus(lambda: self.mb.value, self.mmio_read, self.mmio_write)
        self.devices: list[Device] = []
        if enabled_devices.get("pit", False): self.devices.append(PIT())
        if enabled_devices.get("rtc", False): self.devices.append(RTC())
        if enabled_devices.get("disk", False): self.devices.append(Disk(image_file, self.bus))

        # graphics and keyboard device (two-in-one via pygame)
        if enabled_devices.get("graphics", False):
            _key_queue = deque()
            self.devices.append(Graphics(_key_queue, self.bus.vram_view, lambda: self.running, self.shutdown))
            self.devices.append(Keyboard(_key_queue))

        # debugger etc.
        self.breakpoints: set[int] = set[int]()  # empty set of breakpoints
        self.halted: bool = False  # hardware halt
        self.running = False  # true only while the run loop is active


        # handlers keyed by mnemonic; dispatch via OPCODE_FORMATS[opcode].mnemonic
        from .handlers import handler_map
        self.handlers: dict[INSTRUCTIONS, Callable[[Emulator, tuple[int, ...]], None]] = handler_map

    # memory
    def load_binary(self, file: str, addr: int = 0):

        # check if file exists
        if not os.path.exists(file):
            logger.error(f"file {file} does not exist.")
            return

        # get binary data from file
        with open(file, "rb") as f:
            binary = f.read()

        # load 'er up
        self.bus.load_bytes(addr, binary)
        logger.info(f"loaded {len(binary)} bytes to 0x{addr:04X}.")

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
            self.reset() if value == 0x01 else self.shutdown() if value == 0x02 else None

        for device in self.devices:
            if addr in device.write_dispatch:
                device.mmio_write(addr, value)
                break

    def reset(self) -> None:
        self.bus.reset()

        # reset registers
        for register in self.reg.values():
            register.set(0)
        self.sp.set(0xFDFF)
        self.halted = False

        for device in self.devices:
            device.reset()

        logger.info("emulator reset!")


    def shutdown(self) -> None:
        print("shutting down...")
        sys.exit(0)

    # main fetch/decode

    def fetch(self) -> int:
        # fetch word and increment program counter
        value = self.bus.read16(self.pc.value)
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

        self.running = True
        try:
            while True:
                # normal execution
                time.sleep(0)
                self.step()
        except EmulatorException as e:
            # we enter exceptional control flow either if something went wrong,
            # or if the user interrupts the program
            logger.error(f"emulator stopped: {e.message} (at 0x{self.pc.value:04X}).")
        except KeyboardInterrupt:
            # prevent ctrl+c from bubbling up to the __main__() function,
            # allowing easy program interruption, etc. while allowing the repl to persist
            logger.info("! execution stopped (user interrupt).")
        except Exception as e:
            # general exception. this is an emulator code error, 
            # not an assembly error. allow the repl to persist.
            logger.error(f"fatal! while running instruction at 0x{(self.pc.value)}:\n{traceback.format_exc()}")
        finally:
            self.running = False


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
        overflow = 1 if (((a ^ b) & 0x8000) == 0 and ((a ^ result) & 0x8000) != 0) else 0
        self.set_all_flags(result == 0, carry, result & 0x8000 != 0, overflow)
        return result


    def _sub_core(self, a: int, b: int, borrow_in: int = 0) -> int:
        full = a - b - borrow_in
        result = mask16(full)
        carry = 1 if a >= b + borrow_in else 0
        overflow = 1 if (((a ^ b) & 0x8000) != 0 and ((a ^ result) & 0x8000) != 0) else 0
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
        self.bus.write16(self.sp.value, value)


    def _pop_core(self) -> int:
        value = self.bus.read16(self.sp.value)  # read value from stack
        self.sp.set(self.sp.value + 1)  # increment stack pointer
        self.flag_set(FLAG_Z, value == 0)
        return value
