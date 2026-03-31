# emulator.py
# jaide emulator
# josiah bergen, january 2026

import os
import signal
import sys
import time
from typing import Callable
from multiprocessing import shared_memory, Process, Queue
from multiprocessing.synchronize import Event
from queue import Empty

from common.isa import INSTRUCTIONS, MODES, OPCODE_FORMATS
from .constants import (
    MEMORY_SIZE, BANK_SIZE, NUM_BANKS, REGISTERS,
    FLAG_C, FLAG_Z, FLAG_N, FLAG_O, FLAG_I,
)
from .exceptions import EmulatorException
from .register import Register
from .util.logger import logger

def mask16(x: int) -> int: return x & 0xFFFF # mask to 16 bits

class Emulator:

    def __init__(self):

        # general purpose registers
        self.reg: dict[str, Register] = {reg: Register(reg, 0) for reg in REGISTERS}

        # special registers
        self.pc: Register = self.reg["PC"] # program counter
        self.sp: Register = self.reg["SP"] # stack pointer
        self.f: Register = self.reg["F"] # flags
        self.mb: Register = self.reg["MB"] # memory bank

        # set stack pointer to 0xFEFF as recommended by the spec
        self.sp.set(0xFEFF)

        # memory and i/o
        self.memory: bytearray = bytearray(MEMORY_SIZE)
        
        # VRAM lives in shared memory so the graphics process can map the same buffer
        self.vram_shm = shared_memory.SharedMemory(create=True, size=BANK_SIZE)
        self.vram: memoryview = memoryview(self.vram_shm.buf)
        self.banks: list[bytearray | memoryview] = [self.vram] + [
            bytearray(BANK_SIZE) for _ in range(NUM_BANKS - 1)
        ]

        # 256 16-bit ports
        self.ports: list[int] = [0] * 256 
                
        # interrupt handling
        self.pending_interrupts: list[int] = [] # queue of vectors waiting to be handled
        self.waiting_for_interrupt: bool = False
        self.flag_set(FLAG_I, True)
        
        # debugger etc.
        self.breakpoints: set[int] = set[int]() # empty set of breakpoints
        self.halted: bool = False # hardware halt (not waiting for interrupt
        
        # handlers keyed by mnemonic; dispatch via OPCODE_FORMATS[opcode].mnemonic
        self.handlers: dict[INSTRUCTIONS, Callable[[tuple[int, ...]], None]] = {}
        self._populate_handlers()

        # optional graphics-related attributes (set by __main__ when graphics is enabled)
        self.key_queue: Queue | None = None
        self.gfx_stop_event: Event | None = None
        self.gfx_proc: Process | None = None

    def _release_shared_vram(self) -> None:
        try:
            self.vram.release()
            self.vram_shm.close()
            self.vram_shm.unlink()
        except (FileNotFoundError, BufferError):
            pass
        except Exception:
            pass

    def __del__(self):
        self._release_shared_vram()

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

        self.memory[addr:addr+len(binary)] = binary
        print(f"loaded {len(binary)} bytes to 0x{addr:04X}.")
    
    def read16(self, addr: int) -> int: 
        # fetch a 16-bit little-endian value from memory using word addressing
        bank = self.mb.value % 32
        memory = self.banks[bank - 1] if bank != 0 and 0x0200 <= addr < 0x4200 else self.memory
        addr = addr - 0x0200 if 0x0200 <= addr < 0x4200 else addr

        lo = memory[addr * 2]
        hi = memory[addr * 2 + 1]
        return (hi << 8) | lo

    def write16(self, addr: int, value: int):
        # write a 16-bit little-endian value to memory using word addressing

        if addr < 0x0200: # writing to ROM (0x0000–0x01FF)
            logger.warning(f"write to ROM at 0x{addr:04X}.", "write16")
            return
        
        bank = self.mb.value % 32
        memory = self.banks[bank - 1] if bank != 0 and 0x0200 <= addr < 0x4200 else self.memory
        addr = addr - 0x0200 if 0x0200 <= addr < 0x4200 else addr

        if addr * 2 >= len(memory):
            logger.error(f"attempted to write to out of bounds memory (0x{addr*2:04X} in bank {bank}). halting.")
            self.halted = True
            return
 
        value = mask16(value)
        memory[addr * 2] = value & 0xFF
        memory[addr * 2 + 1] = (value >> 8) & 0xFF

    def split_word(self, word: int) -> tuple[int, int]:
        # returns low, high
        return word & 0xFF, (word >> 8) & 0xFF

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
        return mask16(self.ports[port])
    
    def port_set(self, port: int, value: int) -> None:
        value = mask16(value)
        if port == 0: # port 0 is special and will print the value to the console
            print(chr(value), end="", flush=True)

        if port == 0xFF: # system interface port
            match value:
                case 0x01: # reset
                    self.reset()
                case 0x02: # halt
                    self.halted = True
                case 0x03: # power off
                    self.shutdown()
                case _:
                    pass # undefined behavior, so we'll just do nothing
        self.ports[port] = value

    # interrupt helpers
    def request_interrupt(self, vector: int) -> None:
        if self.halted:
            return
        if vector < 0 or vector > 0xFF:
            raise EmulatorException(f"invalid interrupt vector {vector}. valid vectors are 0-255.")
        
        self.pending_interrupts.append(vector)

    def interrupts_pending(self) -> bool:
        return len(self.pending_interrupts) > 0 and self.flag_get(FLAG_I)

    def reset(self) -> None:
        self.__init__()
        print("emulator reset")

    def shutdown(self) -> None:
        print("shutting down...")

        # stop graphics process if running
        if self.gfx_stop_event is not None:
            self.gfx_stop_event.set()
        if self.gfx_proc is not None:
            self.gfx_proc.join(timeout=1.0)

        self._release_shared_vram()

        sys.exit(0)

    # main fetch/decode
    def fetch(self) -> int:
        # fetch word and increment program counter
        value = self.read16(self.pc.value)
        self.pc.set(self.pc.value + 1)
        return value

    @staticmethod
    def _signed16(x: int) -> int:
        """ Interpret a 16-bit unsigned value as a signed integer. """
        return x if x < 0x8000 else x - 0x10000

    def decode(self) -> tuple[int, ...]:
        word  = self.fetch()
        regs, instr = self.split_word(word)

        opcode = instr                      # flat 8-bit opcode
        reg_a  = (regs >> 4) & 0xF         # ssss — high nibble
        reg_b  = regs & 0xF                # dddd — low nibble

        if opcode not in OPCODE_FORMATS:
            logger.warning(f"invalid opcode 0x{opcode:02x} at 0x{self.pc.value:04x}. requesting interrupt 1.")
            self.request_interrupt(1) # invalid instruction interrupt
            self.halted = True
            return (0, 0, 0, 0)

        fmt   = OPCODE_FORMATS[opcode]
        imm16 = self.fetch() if fmt.imm is not None else 0

        return opcode, reg_a, reg_b, imm16

    # main run loop
    def run(self) -> None:

        # set up signal handler, regular KeyboardInterrupt corrupts the
        # console state on windows :(
        self._interrupted = False
        prev_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, lambda *_: setattr(self, '_interrupted', True))
        
        try:
            while not self._interrupted:
                self.step()
        except EmulatorException as e:
            # we enter exceptional control flow either if something went wrong,
            # or if the user interrupts the program (see signal handler above)
            print(f"emulator stopped: {e.message}")
        finally:
            signal.signal(signal.SIGINT, prev_handler)
            self.halted = True

    def step(self) -> None:

        # hardware-level overrides
        if self.halted:
            raise EmulatorException("halted")
        if self.pc in self.breakpoints:
            raise EmulatorException(f"hit breakpoint at 0x{self.pc:04X}")

        if self.interrupts_pending():
            # interrupt called!
            self.waiting_for_interrupt = False # reset to normal execution state
            interrupt_id = self.pending_interrupts.pop(0)
            self._execute_interrupt(interrupt_id)
            return # cycle done, go to next instruction

        # poll graphics keyboard input if graphics controller is running
        # (important: HALT's waiting state returns early, so we must poll before that)
        if self.key_queue is not None:
            try:
                while True:
                    keycode = self.key_queue.get_nowait()
                    self.ports[1] = keycode
                    self.request_interrupt(4)
            except Empty:
                pass

        if self.waiting_for_interrupt: # i.e. halt was called, we are simply waiting for an interrupt
            # If the keyboard queue caused an interrupt request, service it immediately.
            if self.interrupts_pending():
                self.waiting_for_interrupt = False
                interrupt_id = self.pending_interrupts.pop(0)
                self._execute_interrupt(interrupt_id)
                return

            time.sleep(1 / 60) # reduce cpu usage a little
            return

        # normal execution
        decoded = self.decode()
        opcode  = decoded[0]
        self.handlers[OPCODE_FORMATS[opcode].mnemonic](decoded)



    # core helpers

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
        value = self.read16(self.sp.value) # read value from stack
        self.sp.set(self.sp.value + 1) # increment stack pointer
        self.flag_set(FLAG_Z, value == 0)
        return value

    def _execute_interrupt(self, vector: int) -> None:
        if vector < 0 or vector > 0xFF:
            raise EmulatorException(f"invalid interrupt vector {vector}. valid vectors are 0-255.")
        
        # interrupts gotta be enabled
        if not self.flag_get(FLAG_I):
            print(f"interrupt {vector} ignored, mask is {self.flag_get(FLAG_I)}")
            return

        # push pc and flags
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


    # operation handlers
    # decoded is always (opcode, reg_a, reg_b, imm16)
    # reg_a = ssss (high nibble), reg_b = dddd (low nibble)
    # see OPCODE_FORMATS for which operand each field represents per opcode.

    def handle_halt(self, decoded: tuple[int, ...]) -> None:
        self.waiting_for_interrupt = True

    def handle_get(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        # reg_a = ssss = src ptr register, reg_b = dddd = dest register
        if modes == (MODES.REG, MODES.REG_POINTER):
            # dest <- [src_ptr]
            self.reg_set(reg_b, self.read16(self.reg_get(reg_a)))
        elif modes == (MODES.REG, MODES.REL_POINTER):
            # dest <- [pc + offset]  (imm16 is signed offset to label)
            addr = mask16(self.pc.value + self._signed16(imm16))
            self.reg_set(reg_b, self.read16(addr))
        elif modes == (MODES.REG, MODES.OFF_POINTER):
            # dest <- [label + ptr_reg]  (imm16 is signed offset to base label)
            base = mask16(self.pc.value + self._signed16(imm16))
            self.reg_set(reg_b, self.read16(mask16(base + self.reg_get(reg_a))))
        else:
            raise EmulatorException(f"unexpected GET variant at 0x{self.pc.value:04x}.")

    def handle_put(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        # reg_a = ssss = src register, reg_b = dddd = dest ptr register
        if modes == (MODES.REG_POINTER, MODES.REG):
            # [dest_ptr] <- src
            self.write16(self.reg_get(reg_b), self.reg_get(reg_a))
        elif modes == (MODES.OFF_POINTER, MODES.REG):
            # [label + dest_ptr] <- src
            base = mask16(self.pc.value + self._signed16(imm16))
            self.write16(mask16(base + self.reg_get(reg_b)), self.reg_get(reg_a))
        elif modes == (MODES.REL_POINTER, MODES.REG):
            # [pc + imm] <- src  (position-independent store to label)
            addr = mask16(self.pc.value + self._signed16(imm16))
            self.write16(addr, self.reg_get(reg_a))
        else:
            raise EmulatorException(f"unexpected PUT variant at 0x{self.pc.value:04x}.")

    def handle_mov(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            # dest(reg_b) <- src(reg_a)
            self.reg_set(reg_b, self.reg_get(reg_a))
        elif modes == (MODES.REG, MODES.IMM):
            # dest(reg_a) <- imm  [dest is in ssss slot for imm variants]
            self.reg_set(reg_a, imm16)
        elif modes == (MODES.REG, MODES.RELATIVE):
            # dest(reg_a) <- address of label
            self.reg_set(reg_a, mask16(self.pc.value + self._signed16(imm16)))
        else:
            raise EmulatorException(f"unexpected MOV variant at 0x{self.pc.value:04x}.")

    def handle_push(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG,):
            self._push_core(self.reg_get(reg_a))
        elif modes == (MODES.IMM,):
            self._push_core(imm16)
        else:
            raise EmulatorException(f"unexpected PUSH variant at 0x{self.pc.value:04x}.")

    def handle_pop(self, decoded: tuple[int, ...]) -> None:
        _, reg_a, reg_b, _ = decoded
        # dest is in dddd slot (reg_b)
        self.reg_set(reg_b, self._pop_core())

    def handle_add(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        # dest = reg_b (dddd), src = reg_a (ssss) or imm
        if modes == (MODES.REG, MODES.REG):
            result = self._add_core(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            result = self._add_core(self.reg_get(reg_b), imm16)
        self.reg_set(reg_b, result)

    def handle_adc(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        carry = int(self.flag_get(FLAG_C))
        if modes == (MODES.REG, MODES.REG):
            result = self._add_core(self.reg_get(reg_b), self.reg_get(reg_a), carry)
        else:
            result = self._add_core(self.reg_get(reg_b), imm16, carry)
        self.reg_set(reg_b, result)

    def handle_sub(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self._sub_core(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            result = self._sub_core(self.reg_get(reg_b), imm16)
        self.reg_set(reg_b, result)

    def handle_sbc(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        borrow = int(self.flag_get(FLAG_C))
        if modes == (MODES.REG, MODES.REG):
            result = self._sub_core(self.reg_get(reg_b), self.reg_get(reg_a), borrow)
        else:
            result = self._sub_core(self.reg_get(reg_b), imm16, borrow)
        self.reg_set(reg_b, result)

    def handle_mul(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        dest = self.reg_get(reg_b)
        src  = self.reg_get(reg_a) if modes == (MODES.REG, MODES.REG) else imm16
        full   = dest * src
        result = mask16(full)
        carry  = 1 if full > 0xFFFF else 0
        self.set_all_flags(result == 0, carry, result & 0x8000 != 0, 0)
        self.reg_set(reg_b, result)

    def handle_mod(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        dest = self.reg_get(reg_b)
        src  = self.reg_get(reg_a) if modes == (MODES.REG, MODES.REG) else imm16
        if src == 0:
            # division by zero, request hardware fault interrupt
            logger.warning(f"division by zero at 0x{self.pc.value:04x}. hardware fault interrupt called.")
            self.request_interrupt(0)
            return
        result = mask16(dest % src)
        self.set_all_flags(result == 0, 0, result & 0x8000 != 0, 0)
        self.reg_set(reg_b, result)

    def handle_div(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        dest = self.reg_get(reg_b)
        src  = self.reg_get(reg_a) if modes == (MODES.REG, MODES.REG) else imm16

        if src == 0:
            logger.warning(f"division by zero at 0x{self.pc.value:04x}. hardware fault interrupt called.")
            self.request_interrupt(0)
            return

        result    = mask16(dest // src)
        remainder = dest % src

        self.set_all_flags(result == 0, remainder != 0, result & 0x8000 != 0, 0)
        self.reg_set(reg_b, result)

    def handle_inc(self, decoded: tuple[int, ...]) -> None:
        _, reg_a, reg_b, _ = decoded
        # dest is in dddd slot (reg_b)
        result = self._add_core(self.reg_get(reg_b), 1)
        self.reg_set(reg_b, result)

    def handle_dec(self, decoded: tuple[int, ...]) -> None:
        _, reg_a, reg_b, _ = decoded
        # dest is in dddd slot (reg_b)
        result = self._sub_core(self.reg_get(reg_b), 1)
        self.reg_set(reg_b, result)

    def handle_lsh(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self._lsh_core(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            result = self._lsh_core(self.reg_get(reg_b), imm16)
        self.reg_set(reg_b, result)

    def handle_rsh(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self._rsh_core(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            result = self._rsh_core(self.reg_get(reg_b), imm16)
        self.reg_set(reg_b, result)

    def handle_asr(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self._asr_core(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            result = self._asr_core(self.reg_get(reg_b), imm16)
        self.reg_set(reg_b, result)

    def handle_and(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self.reg_get(reg_b) & self.reg_get(reg_a)
        else:
            result = self.reg_get(reg_b) & imm16
        self.reg_set(reg_b, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_or(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self.reg_get(reg_b) | self.reg_get(reg_a)
        else:
            result = self.reg_get(reg_b) | imm16
        self.reg_set(reg_b, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_not(self, decoded: tuple[int, ...]) -> None:
        _, reg_a, reg_b, _ = decoded
        # dest is in dddd slot (reg_b)
        result = mask16(~self.reg_get(reg_b))
        self.reg_set(reg_b, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_xor(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG, MODES.REG):
            result = self.reg_get(reg_b) ^ self.reg_get(reg_a)
        else:
            result = self.reg_get(reg_b) ^ imm16
        self.reg_set(reg_b, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_swp(self, decoded: tuple[int, ...]) -> None:
        _, reg_a, reg_b, _ = decoded
        # reg_a = ssss = op0, reg_b = dddd = op1
        a, b = self.reg_get(reg_a), self.reg_get(reg_b)
        self.reg_set(reg_a, b)
        self.reg_set(reg_b, a)

    def handle_inb(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        # dest = reg_b (dddd), port = reg_a (ssss) or imm
        if modes == (MODES.REG, MODES.REG):
            result = self.port_get(self.reg_get(reg_a))
        else:
            result = self.port_get(imm16)
        self.reg_set(reg_b, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_outb(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        # src = reg_a (ssss), port = reg_b (dddd) or imm
        if modes == (MODES.REG, MODES.REG):
            self.port_set(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            # OUTB imm, reg: port = imm, src = reg_a
            self.port_set(imm16, self.reg_get(reg_a))

    def handle_cmp(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        # spec: flags <- dest - src
        # reg+reg: src=reg_a(ssss), dest=reg_b(dddd)
        # reg+imm: src=imm,  dest=reg_a(ssss) [dest in ssss anomaly]
        if modes == (MODES.REG, MODES.REG):
            self._sub_core(self.reg_get(reg_b), self.reg_get(reg_a))
        else:
            self._sub_core(self.reg_get(reg_b), imm16)

    def _jump_target(self, imm16: int) -> int:
        """ Compute absolute jump target from a signed relative offset. """
        return mask16(self.pc.value + self._signed16(imm16))

    def handle_jmp(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        if modes == (MODES.REG,):
            self.pc.set(self.reg_get(reg_a))
        elif modes == (MODES.IMM,):
            self.pc.set(imm16)
        elif modes == (MODES.RELATIVE,):
            self.pc.set(self._jump_target(imm16))
        elif modes == (MODES.OFF_POINTER,):
            base = self._jump_target(imm16)
            self.pc.set(self.read16(mask16(base + self.reg_get(reg_a))))
        else:
            raise EmulatorException(f"unexpected JMP variant at 0x{self.pc.value:04x}.")

    def _cond_jump(self, condition: bool, decoded: tuple[int, ...]) -> None:
        if condition:
            _, reg_a, reg_b, imm16 = decoded
            self.pc.set(self._jump_target(imm16))

    # init tests are for the weak
    def handle_jz(self,  decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_Z), decoded)
    def handle_jnz(self, decoded: tuple[int, ...]) -> None: self._cond_jump(not self.flag_get(FLAG_Z), decoded)
    def handle_jc(self,  decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_C), decoded)
    def handle_jnc(self, decoded: tuple[int, ...]) -> None: self._cond_jump(not self.flag_get(FLAG_C), decoded)
    def handle_ja(self,  decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_C) and not self.flag_get(FLAG_Z), decoded)
    def handle_jae(self, decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_C) or self.flag_get(FLAG_Z), decoded)
    def handle_jb(self,  decoded: tuple[int, ...]) -> None: self._cond_jump(not self.flag_get(FLAG_C), decoded)
    def handle_jbe(self, decoded: tuple[int, ...]) -> None: self._cond_jump(not self.flag_get(FLAG_C) or self.flag_get(FLAG_Z), decoded)
    def handle_jg(self,  decoded: tuple[int, ...]) -> None: self._cond_jump(not self.flag_get(FLAG_Z) and ((self.flag_get(FLAG_N) == self.flag_get(FLAG_O))), decoded)
    def handle_jge(self, decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_N) ==  self.flag_get(FLAG_O), decoded)
    def handle_jl(self,  decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_N) !=  self.flag_get(FLAG_O), decoded)
    def handle_jle(self, decoded: tuple[int, ...]) -> None: self._cond_jump(    self.flag_get(FLAG_Z) or  (self.flag_get(FLAG_N) != self.flag_get(FLAG_O)), decoded)

    def handle_call(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes
        self._push_core(self.pc.value)
        if modes == (MODES.REG,):
            self.pc.set(self.reg_get(reg_a))
        elif modes == (MODES.RELATIVE,):
            self.pc.set(self._jump_target(imm16))
        elif modes == (MODES.OFF_POINTER,):
            base = self._jump_target(imm16)
            self.pc.set(self.read16(mask16(base + self.reg_get(reg_a))))
        else:
            raise EmulatorException(f"unexpected CALL variant at 0x{self.pc.value:04x}.")

    def handle_ret(self, decoded: tuple[int, ...]) -> None:
        self.pc.set(self._pop_core())

    def handle_int(self, decoded: tuple[int, ...]) -> None:
        opcode, reg_a, reg_b, imm16 = decoded
        modes = OPCODE_FORMATS[opcode].modes

        if not self.flag_get(FLAG_I):
            return

        vector = self.reg_get(reg_a) if modes == (MODES.REG,) else imm16
        self._execute_interrupt(vector)

    def handle_iret(self, decoded: tuple[int, ...]) -> None:
        self.f.set(self._pop_core())
        self.pc.set(self._pop_core())

    def handle_nop(self, decoded: tuple[int, ...]) -> None:
        pass

    def _populate_handlers(self) -> None:
        self.handlers[INSTRUCTIONS.HALT] = self.handle_halt
        self.handlers[INSTRUCTIONS.GET]  = self.handle_get
        self.handlers[INSTRUCTIONS.PUT]  = self.handle_put
        self.handlers[INSTRUCTIONS.MOV]  = self.handle_mov
        self.handlers[INSTRUCTIONS.PUSH] = self.handle_push
        self.handlers[INSTRUCTIONS.POP]  = self.handle_pop
        self.handlers[INSTRUCTIONS.ADD]  = self.handle_add
        self.handlers[INSTRUCTIONS.ADC]  = self.handle_adc
        self.handlers[INSTRUCTIONS.SUB]  = self.handle_sub
        self.handlers[INSTRUCTIONS.SBC]  = self.handle_sbc
        self.handlers[INSTRUCTIONS.MUL]  = self.handle_mul
        self.handlers[INSTRUCTIONS.MOD]  = self.handle_mod
        self.handlers[INSTRUCTIONS.DIV]  = self.handle_div
        self.handlers[INSTRUCTIONS.INC]  = self.handle_inc
        self.handlers[INSTRUCTIONS.DEC]  = self.handle_dec
        self.handlers[INSTRUCTIONS.LSH]  = self.handle_lsh
        self.handlers[INSTRUCTIONS.RSH]  = self.handle_rsh
        self.handlers[INSTRUCTIONS.ASR]  = self.handle_asr
        self.handlers[INSTRUCTIONS.AND]  = self.handle_and
        self.handlers[INSTRUCTIONS.OR]   = self.handle_or
        self.handlers[INSTRUCTIONS.NOT]  = self.handle_not
        self.handlers[INSTRUCTIONS.XOR]  = self.handle_xor
        self.handlers[INSTRUCTIONS.SWP]  = self.handle_swp
        self.handlers[INSTRUCTIONS.INB]  = self.handle_inb
        self.handlers[INSTRUCTIONS.OUTB] = self.handle_outb
        self.handlers[INSTRUCTIONS.CMP]  = self.handle_cmp
        self.handlers[INSTRUCTIONS.JMP]  = self.handle_jmp
        self.handlers[INSTRUCTIONS.JZ]   = self.handle_jz
        self.handlers[INSTRUCTIONS.JNZ]  = self.handle_jnz
        self.handlers[INSTRUCTIONS.JC]   = self.handle_jc
        self.handlers[INSTRUCTIONS.JNC]  = self.handle_jnc
        self.handlers[INSTRUCTIONS.JA]   = self.handle_ja
        self.handlers[INSTRUCTIONS.JAE]  = self.handle_jae
        self.handlers[INSTRUCTIONS.JB]   = self.handle_jb
        self.handlers[INSTRUCTIONS.JBE]  = self.handle_jbe
        self.handlers[INSTRUCTIONS.JG]   = self.handle_jg
        self.handlers[INSTRUCTIONS.JGE]  = self.handle_jge
        self.handlers[INSTRUCTIONS.JL]   = self.handle_jl
        self.handlers[INSTRUCTIONS.JLE]  = self.handle_jle
        self.handlers[INSTRUCTIONS.CALL] = self.handle_call
        self.handlers[INSTRUCTIONS.RET]  = self.handle_ret
        self.handlers[INSTRUCTIONS.INT]  = self.handle_int
        self.handlers[INSTRUCTIONS.IRET] = self.handle_iret
        self.handlers[INSTRUCTIONS.NOP]  = self.handle_nop
