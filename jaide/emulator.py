# emulator.py
# jaide emulator
# josiah bergen, january 2026

import os
import sys
import time
from typing import Callable

from .constants import (
    MNEMONICS, INSTRUCTION_ENCODINGS,
    MEMORY_SIZE, BANK_SIZE, NUM_BANKS, REGISTERS, LOC, FLAG_C, FLAG_Z, FLAG_N, FLAG_O, FLAG_I,
    OP_HALT, OP_GET, OP_PUT, OP_MOV, OP_PUSH, OP_POP, OP_ADD, OP_ADC, OP_SUB, OP_SBC,
    OP_INC, OP_DEC, OP_LSH, OP_RSH, OP_AND, OP_OR, OP_NOR, OP_NOT, OP_XOR, OP_INB, OP_OUTB,
    OP_CMP, OP_JMP, OP_JZ, OP_JNZ, OP_JC, OP_JNC, OP_CALL, OP_RET, OP_INT, OP_IRET, OP_NOP,
    MODE_NULL, MODE_REG, MODE_IMM16, MODE_MEM_INDIRECT, MODE_MEM_DIRECT,
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
        
        # memory banks and ports
        self.banks: list[bytearray] = [bytearray(BANK_SIZE) for _ in range(NUM_BANKS)]
        self.vram: memoryview = memoryview(self.banks[0]) # special reference to VRAM bank

        # 256 16-bit ports
        self.ports: list[int] = [0] * 256 
                
        # interrupt handling
        self.pending_interrupts: list[int] = [] # queue of vectors waiting to be handled
        self.waiting_for_interrupt: bool = False
        self.flag_set(FLAG_I, True)
        
        # debugger etc.
        self.breakpoints: set[int] = set[int]() # empty set of breakpoints
        self.halted: bool = False # hardware halt (not waiting for interrupt
        
        # handlers for each opcode, abstracted elsewhere
        self.handlers: dict[int, Callable[[tuple[int, ...]]]] = {}
        self._populate_handlers()


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
        memory = self.banks[bank - 1] if bank != 0 and 0x8000 <= addr < 0xC000 else self.memory
        addr = addr - 0x8000 if 0x8000 <= addr < 0xC000 else addr
        
        lo = memory[addr * 2]
        hi = memory[addr * 2 + 1]
        return (hi << 8) | lo

    def write16(self, addr: int, value: int):
        # write a 16-bit little-endian value to memory using word addressing

        if addr < 0x8000: # writing to ROM
            logger.warning(f"write to ROM at 0x{addr:04X}.", "write16")
            return
        
        bank = self.mb.value % 32
        memory = self.banks[bank - 1] if bank != 0 and 0x8000 <= addr < 0xC000 else self.memory
        addr = addr - 0x8000 if 0x8000 <= addr < 0xC000 else addr

        if addr * 2 >= len(memory):
            logger.error(f"attempted to write to out of bounds memory (0x{addr*2:04X} in bank {bank}). halting.")
            self.halted = True
            return
 
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
        self.reg[REGISTERS[index]].set(value)

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
        self.memory[0x8000:] = bytearray(MEMORY_SIZE - 0x8000) # clear ram (0x8000-0xFFFF inclusive)
        for bank in self.banks: bank[:] = bytearray(BANK_SIZE) # noqa: E701
        self.ports = [0] * 256 # reset ports
        self.reg = {reg: Register(reg, 0) for reg in REGISTERS} # re-initialize registers
        self.sp.set(0xFEFF)
        self.pc.set(0)
        self.halted = False

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
        regs, instr = self.split_word(word)
        
        opcode = (instr >> 2) & 0b111111
        mode = instr & 0b11
        reg_a = (regs >> 4) & 0xF
        reg_b = regs & 0xF
        imm16 = 0

        if mode not in INSTRUCTION_ENCODINGS[opcode]:
            logger.error(f"invalid addressing mode {mode} for {MNEMONICS[opcode]} at {self.pc}. halting.")
            return (0, 0, 0, 0, 0)

        if INSTRUCTION_ENCODINGS[opcode][mode][LOC.IMM16] is not None:
            imm16 = self.fetch()

        return opcode, mode, reg_a, reg_b, imm16

    # main run loop
    def run(self) -> None:
            try:
                while True:
                    # normal execution
                    self.step()
            except EmulatorException as e:
                # we enter exceptional control flow either if something went wrong,
                # or if the user interrupts the program
                print(f"emulator stopped: {e.message}")
            except KeyboardInterrupt:
                # this prevents ctrl+c from bubbling up to the __main__() function,
                # allowing easy program interruption, etc. while allowing the repl to persist
                print("execution stopped.")
            finally:
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

        if self.waiting_for_interrupt: # i.e. halt was called, we are simply waiting for an interrupt
            time.sleep(1 / 60) # reduce cpu usage a little
            return

        # normal execution
        decoded = self.decode() # decode instruction
        opcode = decoded[0]
        self.handlers[opcode](decoded) # run instruction handler


    def assert_addressing_mode(self, actual: int, expected: int | list[int]) -> None:
        if isinstance(expected, int):
            expected = [expected]
        if actual not in expected:
            expected_string = "any of " + ", ".join([str(m) for m in expected]) if len(expected) > 1 else str(expected[0])
            raise EmulatorException(f"invalid addressing mode {actual} at 0x{self.pc:04X} (expected {expected_string}, got {actual}: {actual:08b}).")

    def get_mode(self, decoded: tuple[int, ...]) -> int:
        # decoded is always a tuple of (opcode, mode, *operands)
        return decoded[1]

    # core helpers

    def _add_core(self, a: int, b: int, carry_in: int = 0) -> int:
        full = a + b + carry_in
        result = mask16(full)
        carry = 1 if full > 0xFFFF else 0
        overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
        self.set_all_flags(result == 0, carry, result < 0, overflow)
        return result

    def _sub_core(self, a: int, b: int, borrow_in: int = 0) -> int:
        full = a - b - borrow_in
        result = mask16(full)
        carry = 1 if a >= b + borrow_in else 0
        overflow = 1 if (((a ^ b) & 0x80) != 0 and ((a ^ result) & 0x80) != 0) else 0
        self.set_all_flags(result == 0, carry, result < 0, overflow)
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

    def handle_halt(self, decoded: tuple[int, ...]) -> None:
        _, mode, _, _, _ = decoded
        # MODE_NULL: HALT
        if mode == MODE_NULL:
            self.waiting_for_interrupt = True
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for HALT at 0x{self.pc:04X}.")

    def handle_get(self, decoded: tuple[int, ...]) -> str | None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_MEM_INDIRECT: RA <- [RB]
        # MODE_MEM_DIRECT: RA <- [IMM16]
        if mode == MODE_MEM_INDIRECT:
            self.reg_set(reg_a, self.read16(self.reg_get(reg_b)))
        elif mode == MODE_MEM_DIRECT:
            self.reg_set(reg_a, self.read16(imm16))
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for GET at 0x{self.pc:04X}.")

    def handle_put(self, decoded: tuple[int, ...]) -> str | None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_MEM_INDIRECT: [RA] <- RB
        # MODE_MEM_DIRECT: [IMM16] <- RB
        if mode == MODE_MEM_INDIRECT:
            self.write16(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_MEM_DIRECT:
            self.write16(imm16, self.reg_get(reg_b))
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for PUT at 0x{self.pc:04X}.")
    
    def handle_mov(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RB
        # MODE_IMM16: RA <- IMM16
        if mode == MODE_REG:
            self.reg_set(reg_a, self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            self.reg_set(reg_a, imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for MOV at 0x{self.pc:04X}.")

    def handle_push(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: [SP--] <- RA
        # MODE_IMM16: [SP--] <- IMM16
        if mode == MODE_REG:
            self._push_core(self.reg_get(reg_a))
        elif mode == MODE_IMM16:
            self._push_core(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for PUSH at 0x{self.pc:04X}.")
    
    def handle_pop(self, decoded: tuple[int, ...]) -> None: 
        _, mode, reg_a, _, _ = decoded
        # MODE_REG: RA <- [++SP]
        if mode == MODE_REG:
            self.reg_set(reg_a, self._pop_core())
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for POP at 0x{self.pc:04X}.")

    def handle_add(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA + RB
        # MODE_IMM16: RA <- RA + IMM16
        if mode == MODE_REG:
            result = self._add_core(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            result = self._add_core(self.reg_get(reg_a), imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for ADD at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)

    def handle_adc(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA + RB + C
        # MODE_IMM16: RA <- RA + IMM16 + C
        if mode == MODE_REG:
            result = self._add_core(self.reg_get(reg_a), self.reg_get(reg_b), self.flag_get(FLAG_C))
        elif mode == MODE_IMM16:
            result = self._add_core(self.reg_get(reg_a), imm16, self.flag_get(FLAG_C))
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for ADC at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)

    def handle_sub(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA - RB
        # MODE_IMM16: RA <- RA - IMM16
        if mode == MODE_REG:
            result = self._sub_core(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            result = self._sub_core(self.reg_get(reg_a), imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for SUB at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)

    def handle_sbc(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA - RB - C
        # MODE_IMM16: RA <- RA - IMM16 - C
        if mode == MODE_REG:
            result = self._sub_core(self.reg_get(reg_a), self.reg_get(reg_b), self.flag_get(FLAG_C))
        elif mode == MODE_IMM16:
            result = self._sub_core(self.reg_get(reg_a), imm16, self.flag_get(FLAG_C))
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for SBC at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)

    def handle_inc(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, _ = decoded
        # MODE_REG: RA <- RA + 1
        if mode == MODE_REG:
            result = self._add_core(self.reg_get(reg_a), 1)
            self.reg_set(reg_a, result)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for INC at 0x{self.pc:04X}.")

    def handle_dec(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, _ = decoded
        # MODE_REG: RA <- RA - 1
        if mode == MODE_REG:
            result = self._sub_core(self.reg_get(reg_a), 1)
            self.reg_set(reg_a, result)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for DEC at 0x{self.pc:04X}.")

    def handle_lsh(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA << RB
        # MODE_IMM16: RA <- RA << IMM16
        if mode == MODE_REG:
            result = self._lsh_core(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            result = self._lsh_core(self.reg_get(reg_a), imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for LSH at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)

    def handle_rsh(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA >> RB
        # MODE_IMM16: RA <- RA >> IMM16
        if mode == MODE_REG:
            result = self._rsh_core(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            result = self._rsh_core(self.reg_get(reg_a), imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for RSH at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)

    def handle_and(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA & RB
        # MODE_IMM16: RA <- RA & IMM16
        if mode == MODE_REG:
            result = self.reg_get(reg_a) & self.reg_get(reg_b)
        elif mode == MODE_IMM16:
            result = self.reg_get(reg_a) & imm16
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for AND at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_or(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA | RB
        # MODE_IMM16: RA <- RA | IMM16
        if mode == MODE_REG:
            result = self.reg_get(reg_a) | self.reg_get(reg_b)
        elif mode == MODE_IMM16:
            result = self.reg_get(reg_a) | imm16
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for OR at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_nor(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- ~(RA | RB)
        # MODE_IMM16: RA <- ~(RA | IMM16)
        if mode == MODE_REG:
            result = ~(self.reg_get(reg_a) | self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            result = ~(self.reg_get(reg_a) | imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for NOR at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_not(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: RA <- ~RA
        # MODE_IMM16: RA <- ~IMM16
        if mode == MODE_REG:
            result = ~self.reg_get(reg_a)
        elif mode == MODE_IMM16:
            result = ~imm16
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for NOT at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_xor(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RA ^ RB
        # MODE_IMM16: RA <- RA ^ IMM16
        if mode == MODE_REG:
            result = self.reg_get(reg_a) ^ self.reg_get(reg_b)
        elif mode == MODE_IMM16:
            result = self.reg_get(reg_a) ^ imm16
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for XOR at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)
        self.flag_set(FLAG_Z, result == 0)

    def handle_inb(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- port(RB)
        # MODE_IMM16: RA <- port(IMM16)
        if mode == MODE_REG:
            result = self.port_get(self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            result = self.port_get(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for INB at 0x{self.pc:04X}.")
        self.reg_set(reg_a, result)
        self.flag_set(FLAG_Z, result == 0)
    
    def handle_outb(self, decoded: tuple[int, ...]) -> str | None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: port(RA) <- RB
        # MODE_IMM16: port(IMM16) <- RB
        if mode == MODE_REG:
            self.port_set(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            self.port_set(imm16, self.reg_get(reg_b))
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for OUTB at 0x{self.pc:04X}.")

    def handle_cmp(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: Z, C, O, N <- RA - RB
        # MODE_IMM16: Z, C, O, N <- RA - IMM16
        if mode == MODE_REG:
            _ = self._sub_core(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            _ = self._sub_core(self.reg_get(reg_a), imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for CMP at 0x{self.pc:04X}.")

    def handle_jmp(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA]
        # MODE_IMM16: PC <- [IMM16]
        if mode == MODE_MEM_INDIRECT:
            self.pc.set(self.read16(self.reg_get(reg_a)))
        elif mode == MODE_MEM_DIRECT:
            self.pc.set(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for JMP at 0x{self.pc:04X}.")

    def handle_jz(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA] if Z == 1 else NOP
        # MODE_IMM16: PC <- [IMM16] if Z == 1 else NOP
        if not self.flag_get(FLAG_Z):
            return
        if mode == MODE_MEM_INDIRECT:
            self.pc.set(self.read16(self.reg_get(reg_a)))
        elif mode == MODE_MEM_DIRECT:
            self.pc.set(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for JZ at 0x{self.pc:04X}.")

    def handle_jnz(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA] if Z == 0 else NOP
        # MODE_IMM16: PC <- [IMM16] if Z == 0 else NOP
        if self.flag_get(FLAG_Z):
            return
        if mode == MODE_MEM_INDIRECT:
            self.pc.set(self.read16(self.reg_get(reg_a)))
        elif mode == MODE_MEM_DIRECT:
            self.pc.set(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for JNZ at 0x{self.pc:04X}.")

    def handle_jc(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA] if C == 1 else NOP
        # MODE_IMM16: PC <- [IMM16] if C == 1 else NOP
        if not self.flag_get(FLAG_C):
            return
        if mode == MODE_MEM_INDIRECT:
            self.pc.set(self.read16(self.reg_get(reg_a)))
        elif mode == MODE_MEM_DIRECT:
            self.pc.set(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for JC at 0x{self.pc:04X}.")

    def handle_jnc(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA] if C == 0 else NOP
        # MODE_IMM16: PC <- [IMM16] if C == 0 else NOP
        if self.flag_get(FLAG_C):
            return
        if mode == MODE_MEM_INDIRECT:
            self.pc.set(self.read16(self.reg_get(reg_a)))
        elif mode == MODE_MEM_DIRECT:
            self.pc.set(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for JNC at 0x{self.pc:04X}.")

    def handle_call(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA]
        # MODE_IMM16: PC <- [IMM16]
        if mode == MODE_MEM_INDIRECT:
            self._push_core(self.pc.value)
            self.pc.set(self.read16(self.reg_get(reg_a)))
        elif mode == MODE_MEM_DIRECT:
            self._push_core(self.pc.value)
            self.pc.set(imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for CALL at 0x{self.pc:04X}.")

    def handle_ret(self, decoded: tuple[int, ...]) -> None:
        _, mode, _, _, _ = decoded
        # MODE_NULL: PC <- [++SP]
        if mode == MODE_NULL:
            self.pc.set(self._pop_core())
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for RET at 0x{self.pc:04X}.")

    def handle_int(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, _, imm16 = decoded
        # MODE_REG: PC <- [RA]
        # MODE_IMM16: PC <- [IMM16]

        # check if interrupts are enabled
        if not self.flag_get(FLAG_I):
            return

        # get handler
        if mode == MODE_REG:
            handler = self.reg_get(reg_a)
        elif mode == MODE_IMM16:
            handler = imm16
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for INT at 0x{self.pc:04X}.")
        
        self._execute_interrupt(handler)

    def handle_iret(self, decoded: tuple[int, ...]) -> None:
        _, mode, _, _, _ = decoded
        if mode == MODE_NULL:
            self.f.set(self._pop_core())
            self.pc.set(self._pop_core())
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for IRET at 0x{self.pc:04X}.")

    def handle_nop(self, decoded: tuple[int, ...]) -> None: 
        _, mode, _, _, _ = decoded
        # MODE_NULL: NOP
        if mode != MODE_NULL:
            raise EmulatorException(f"invalid addressing mode {mode} for NOP at 0x{self.pc:04X}.")

    def _populate_handlers(self) -> None:
        self.handlers[OP_HALT] = self.handle_halt
        self.handlers[OP_GET]  = self.handle_get
        self.handlers[OP_PUT]  = self.handle_put
        self.handlers[OP_MOV]  = self.handle_mov
        self.handlers[OP_PUSH] = self.handle_push
        self.handlers[OP_POP]  = self.handle_pop
        self.handlers[OP_ADD]  = self.handle_add
        self.handlers[OP_ADC]  = self.handle_adc
        self.handlers[OP_SUB]  = self.handle_sub
        self.handlers[OP_SBC]  = self.handle_sbc
        self.handlers[OP_INC]  = self.handle_inc
        self.handlers[OP_DEC]  = self.handle_dec
        self.handlers[OP_LSH]  = self.handle_lsh
        self.handlers[OP_RSH]  = self.handle_rsh
        self.handlers[OP_AND]  = self.handle_and
        self.handlers[OP_OR]   = self.handle_or
        self.handlers[OP_NOR]  = self.handle_nor
        self.handlers[OP_NOT]  = self.handle_not
        self.handlers[OP_XOR]  = self.handle_xor
        self.handlers[OP_INB]  = self.handle_inb
        self.handlers[OP_OUTB] = self.handle_outb
        self.handlers[OP_CMP]  = self.handle_cmp
        self.handlers[OP_JMP]  = self.handle_jmp
        self.handlers[OP_JZ]   = self.handle_jz
        self.handlers[OP_JNZ]  = self.handle_jnz
        self.handlers[OP_JC]   = self.handle_jc
        self.handlers[OP_JNC]  = self.handle_jnc
        self.handlers[OP_CALL] = self.handle_call
        self.handlers[OP_RET]  = self.handle_ret
        self.handlers[OP_INT]  = self.handle_int
        self.handlers[OP_IRET] = self.handle_iret
        self.handlers[OP_NOP]  = self.handle_nop
