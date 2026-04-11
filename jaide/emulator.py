# emulator.py
# jaide emulator
# josiah bergen, january 2026

import os
import sys
import time
from collections import deque
from typing import Callable

from common.isa import INSTRUCTIONS, OPCODE_FORMATS

from .constants import (
    BANK_SIZE,
    FLAG_C,
    FLAG_I,
    FLAG_N,
    FLAG_O,
    FLAG_STRINGS,
    FLAG_Z,
    MEMORY_SIZE,
    NUM_BANKS,
    REGISTERS,
)
from .devices.device import Device
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
    def __init__(self, verbosity: int = logger.log_level.INFO, enabled_devices: dict[str, bool] = {}):

        logger.set_level(verbosity)

        # general purpose registers
        self.reg: dict[str, Register] = {reg: Register(reg, 0) for reg in REGISTERS}

        # special registers
        self.pc: Register = self.reg["PC"]  # program counter
        self.sp: Register = self.reg["SP"]  # stack pointer
        self.f: Register = self.reg["F"]    # flags
        self.mb: Register = self.reg["MB"]  # memory bank

        # set stack pointer to 0xFEFF as recommended by the spec
        self.sp.set(0xFEFF)

        # memory and i/o
        self.memory: bytearray = bytearray(MEMORY_SIZE)
        self.banks: list[bytearray] = [bytearray(BANK_SIZE) for _ in range(NUM_BANKS)]

        self.ports: list[int] = [0] * 256
        self.devices: list[Device] = []

        # simple read/write devices
        if enabled_devices.get("pit", False): self.devices.append(PIT(self.raise_interrupt))
        if enabled_devices.get("rtc", False): self.devices.append(RTC(self.raise_interrupt))

        # graphics and keyboard devices
        if enabled_devices.get("graphics", False):
            # shared queue for keyboard and graphics
            # we need this because the keyboard and graphics controllers need to both pull data from the pygame window,
            # and this is the simplest way to do that.
            _key_queue = deque()
            self.devices.append(Graphics(self.raise_interrupt, _key_queue, self.banks[0], self.shutdown))
            self.devices.append(Keyboard(self.raise_interrupt, _key_queue))

        # interrupt handling
        self.pending_interrupts: list[int] = []  # queue of vectors waiting to be handled
        self.waiting_for_interrupt: bool = False
        self.flag_set(FLAG_I, True)

        # debugger etc.
        self.breakpoints: set[int] = set[int]()  # empty set of breakpoints
        self.halted: bool = False  # hardware halt
        self._halted_step_count: int = 0

        # handlers keyed by mnemonic; dispatch via OPCODE_FORMATS[opcode].mnemonic
        from .handlers import handler_map
        self.handlers: dict[INSTRUCTIONS, Callable[[Emulator, tuple[int, ...]], None]] = handler_map

    # memory

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
        bank = self.mb.value % 32
        # banked view (MB != 0): window 0xBC00–0xFDFF maps to the start of banks[MB-1].
        # flat memory (MB == 0): use absolute word addresses.
        if bank != 0 and 0xBC00 <= addr <= 0xFDFF:
            memory = self.banks[bank - 1]
            addr = addr - 0xBC00
        else:
            memory = self.memory

        lo = memory[addr * 2]
        hi = memory[addr * 2 + 1]
        return (hi << 8) | lo


    def write16(self, addr: int, value: int):
        # write a 16-bit little-endian value to memory using word addressing

        if addr < 0x0200:  # writing to ROM (0x0000–0x01FF)
            logger.warning(f"write to ROM at 0x{addr:04X}.", "write16")
            return

        bank = self.mb.value % 32
        if bank != 0 and 0xBC00 <= addr <= 0xFDFF:
            memory = self.banks[bank - 1]
            addr = addr - 0xBC00
        else:
            memory = self.memory

        if addr * 2 >= len(memory):
            logger.warning(f"attempted to write to out of bounds memory (0x{addr * 2:04X} in bank {bank}).")
            self.raise_interrupt(0)
            return

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

    # port helpers

    def port_get(self, port: int) -> int:

        for device in self.devices:
            if port in device.read_dispatch:
                return device.port_read(port)
      
        logger.warning(f"no device found on port {port}, return value is undefined behavior.")
        return 0


    def port_set(self, port: int, value: int) -> None:
        value = mask16(value)
        
        if port == 0:  # port 0 is special and will print the value to the console
            print(chr(value), end="", flush=True)

        if port == 0xFF:  # system interface port
            match value:
                case 0x01:  # reset
                    self.reset()
                case 0x02:  # halt
                    self.halted = True
                case 0x03:  # power off
                    self.shutdown()
                case _:
                    pass  # undefined behavior, so we'll just do nothing

        # TODO: refactor to not be a dumb ahh loop
        for device in self.devices:
            if port in device.read_dispatch:
                device.port_write(port, value)
                break

    # interrupt helpers

    def raise_interrupt(self, vector: int) -> None:
        if self.halted:
            return
        if vector < 0 or vector > 0xFF:
            raise EmulatorException(f"invalid interrupt vector {vector}. valid vectors are 0-255.")

        self.pending_interrupts.append(vector)


    def interrupts_pending(self) -> bool:
        return len(self.pending_interrupts) > 0 and self.flag_get(FLAG_I)


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
        reg_a = (regs >> 4) & 0xF  # ssss — high nibble
        reg_b = regs & 0xF  # dddd — low nibble

        if opcode not in OPCODE_FORMATS:
            logger.warning(f"invalid opcode 0x{opcode:02x} at 0x{self.pc.value:04x}. requesting interrupt 1.")
            self.raise_interrupt(1)  # invalid instruction interrupt
            return (0, 0, 0, 0)

        fmt = OPCODE_FORMATS[opcode]
        imm16 = self.fetch() if fmt.imm_operand is not None else 0

        return opcode, reg_a, reg_b, imm16


    # main run loop
    def run(self) -> None:

        # we can restart while waiting for an interrupt
        # so we communicate that, because communication is key
        if self.waiting_for_interrupt:
            logger.debug("waiting for interrupt...")

        try:
            while True:
                # normal execution
                self.step()
        except EmulatorException as e:
            # we enter exceptional control flow either if something went wrong,
            # or if the user interrupts the program
            logger.error(f"emulator stopped: {e.message}")
            # breakpoints are a deliberate stop — leave halted clear so step/run can continue
        except KeyboardInterrupt:
            # this prevents ctrl+c from bubbling up to the __main__() function,
            # allowing easy program interruption, etc. while allowing the repl to persist
            print("! execution stopped (user interrupt).")


    def step(self) -> None:

        # hardware-level overrides
        if self.halted:
            raise EmulatorException("halted")
        if self.pc.value in self.breakpoints:
            raise EmulatorException(f"hit breakpoint at {self.pc}")

        if logger.level == logger.log_level.VERBOSE:
            time.sleep(0.001)

        if self.interrupts_pending():
            # interrupt called!
            logger.verbose(f"interrupt called! {self.pending_interrupts}")
            interrupt_id = self.pending_interrupts.pop()
            self._execute_interrupt(interrupt_id)

            # reset to normal execution state,
            # and skip to next instruction
            self.waiting_for_interrupt = False
            return 

         # tick all devices
        for device in self.devices:
            device.tick()

        if self.waiting_for_interrupt:
            # halt was called, we are simply waiting for an interrupt
            # reduce cpu usage a little and skip executing any instructions
            # self._halted_step_count = (self._halted_step_count + 1) % 10000000
            # if self._halted_step_count == 0:
            #     logger.verbose("waiting for interrupt...")
            # time.sleep(0.001)
            return

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


    def _execute_interrupt(self, vector: int) -> None:
        if vector < 0 or vector > 0xFF:
            raise EmulatorException(f"invalid interrupt vector {vector}. valid vectors are 0-255.")

        # interrupt flag gotta be enabled
        if not self.flag_get(FLAG_I):
            logger.debug(f"interrupt {vector} ignored, mask is {self.flag_get(FLAG_I)}")
            return

        # push return address and flags onto the stack
        self._push_core(self.pc.value)
        self._push_core(self.f.value)

        # clear interrupt mask
        self.flag_set(FLAG_I, False)

        # get vector (interrupt table is at word addresses 0xFEFF-0xFFFF)
        # Interrupt vector is at word address 0xFFFF - vector
        vector_word = 0xFFFF - vector
        dest = self.read16(vector_word)
        # set program counter to address at vector and unhalt

        self.pc.set(dest)
