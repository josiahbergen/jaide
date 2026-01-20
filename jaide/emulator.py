# jaide.py
# jaide emulator
# josiah bergen, january 2026

from colorama import Fore as f
import os
from typing import Callable

from .constants import (
    MNEMONICS, INSTRUCTION_ENCODINGS,
    MEMORY_SIZE, REGISTERS, LOC, FLAG_C, FLAG_Z, FLAG_N, FLAG_O, FLAG_I,
    OP_HALT, OP_LOAD, OP_STORE, OP_MOVE, OP_PUSH, OP_POP, OP_ADD, OP_ADC, OP_SUB, OP_SBC,
    OP_INC, OP_DEC, OP_SHL, OP_SHR, OP_AND, OP_OR, OP_NOR, OP_NOT, OP_XOR, OP_INB, OP_OUTB,
    OP_CMP, OP_JMP, OP_JZ, OP_JNZ, OP_JC, OP_JNC, OP_CALL, OP_RET, OP_INT, OP_IRET, OP_NOP,
    MODE_REG, MODE_IMM16, MODE_MEM_DIRECT,
)
from .devices.screen import Screen
from .exceptions import EmulatorException
from .core import mask16, _add_core, _sub_core, _shl_core, _shr_core, _push_core, _pop_core
from .register import Register
from .util.logger import logger

class Emulator:

    def __init__(self):

        # general purpose registers
        self.reg: dict[str, Register] = {reg: Register(reg, 0) for reg in REGISTERS}

        # special registers
        self.pc: Register = Register("PC", 0) # program counter
        self.sp: Register = Register("SP", 0xFEFF) # stack pointer
        self.f: Register = Register("F", 0) # flags
        self.mb: Register = Register("MB", 0) # memory bank
        self.z: Register = Register("Z", 0) # zero

        # memory and i/o
        self.memory: bytearray = bytearray(MEMORY_SIZE)
        self.ports: list[int] = [0] * 256 # 256 16-bit ports

        # debugger etc.
        self.breakpoints: set[int] = set[int]()
        self.halted: bool = False

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
        lo = self.memory[addr * 2]
        hi = self.memory[addr * 2 + 1]
        return (hi << 8) | lo

    def write16(self, addr: int, value: int):
        # write a 16-bit little-endian value to memory using word addressing
        self.memory[addr * 2] = value & 0xFF
        self.memory[addr * 2 + 1] = (value >> 8) & 0xFF

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
        flag_mask = (1 if value else 0) << bit
        # resets flag bit to 0 then ors with real value
        self.f.set((self.f.value & ~flag_mask) | flag_mask)

    # port helpers
    def port_get(self, port: int) -> int:
        return mask16(self.ports[port])
    
    def port_set(self, port: int, value: int) -> None:
        value = mask16(value)
        if port == 0: # port 0 is special and will print the value to the console
            print(chr(value), end="", flush=True)
        self.ports[port] = value

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
        reg_a = regs & 0b1111
        reg_b = (regs >> 4) & 0b1111
        imm16 = 0

        if mode not in INSTRUCTION_ENCODINGS[opcode]:
            logger.error(f"invalid addressing mode {mode} for {MNEMONICS[opcode]} at {self.pc}. halting.")
            return (0, 0, 0, 0, 0)

        if INSTRUCTION_ENCODINGS[opcode][mode][LOC.IMM16] is not None:
            imm16 = self.fetch()

        return opcode, mode, reg_a, reg_b, imm16

    # main run loop
    def run(self) -> None:
        while not self.halted:
            try:
                res = self.step()
                if res: 
                    print(res)
                    break
            except KeyboardInterrupt:
                print("keyboard interrupt")
                break

    def step(self) -> str | None:
        if self.halted:
            return "halted"
        if self.pc in self.breakpoints:
            return f"hit breakpoint at 0x{self.pc:04X}"

        decoded = self.decode()
        opcode = decoded[0]

        try:
            self.handlers[opcode](decoded)
        except EmulatorException as e:
            return e.message

    # repl and shell interface
    def repl(self):
        scope = "emulator.py:repl()"
        
        print("jaide emulator shell version 0.0.3")
        print("welcome to the emulator! type 'help' for a list of commands.")

        def assert_num_args(positional: int, opt: int = 0):
            low = positional
            high = positional + opt
            if len(args) < low or len(args) > high:
                logger.error(f"invalid number of arguments for command {command} (expected {low}{'-' + str(high) if high != low else ''}, got {len(args)}).")
                return False
            return True
        
        def parse_integer(index: int, base: int = 10, default: int = 0) -> int:
            if index >= len(args):
                # no argument at expected postion, return default
                return default
            try:
                # parse the argument as an integer
                return int(args[index], base)
            except ValueError:
                # invalid argument, return default
                logger.warning(f"invalid argument for command {command} (expected integer, got \"{args[index]}\").", scope)
                return default

        def help_string(command: str, args: str, message: str):
            command_args = f"{command}{' ' if args else ''}{f.RESET}{args}{f.RESET}"
            return f"{command_args:<30} {message}"

        def disasm_at(addr: int) -> str:
            word = self.read16(addr)
            regs, instr = self.split_word(word)
            opcode, mode, reg_a, reg_b, imm16 = (instr >> 2) & 0b111111, instr & 0b11, regs & 0b1111, (regs >> 4) & 0b1111, 0

            if mode not in INSTRUCTION_ENCODINGS[opcode]:
                return f"{MNEMONICS[opcode]} {mode:02X} (invalid addressing mode)"
            if mode in [MODE_IMM16, MODE_MEM_DIRECT]:
                imm16 = self.read16(addr + 1)

            encoding = INSTRUCTION_ENCODINGS[opcode][mode]
            reg_a_str = f" {REGISTERS[reg_a]}" if encoding[LOC.REGA] is not None else ''
            reg_b_str = f" {REGISTERS[reg_b]}" if encoding[LOC.REGB] is not None else ''
            imm16_str = f" {imm16:04X}" if encoding[LOC.IMM16] is not None else ''
            return f"{MNEMONICS[opcode]}{reg_a_str}{reg_b_str}{imm16_str}"
                
        while True:

            command, *args = input(f"{f.LIGHTWHITE_EX}jaide > {f.RESET}").split()

            match command:

                case "load":
                    if not assert_num_args(1, opt=1): continue # noqa: E701
                    file = args[0]
                    addr = parse_integer(1, base=16, default=0)
                    self.load_binary(file, addr)
                
                case "dev":

                    if not assert_num_args(1): continue # noqa: E701
                    device = args[0]
                    if device == "screen":
                        self.screen = Screen(800, 600)
                    else:
                        logger.error(f"invalid device {device}. valid devices are: screen")
                        continue

                case "run":
                    self.run()
    
                case "step":
                    res = self.step()
                    if res: print(res) # noqa: E701
                
                case "break":
                    if not assert_num_args(1, opt=0): continue # noqa: E701
                    addr = parse_integer(0, base=16)
                    self.breakpoints.add(addr)
                    print(f"set breakpoint at address 0x{addr:04X}.")
                
                case "blist":
                    num = len(self.breakpoints)
                    print(f"found {num} breakpoint{'' if num == 1 else 's'}{':' if num > 0 else '.'}")
                    for addr in self.breakpoints:
                        print(f"0x{addr:04X}: {disasm_at(addr)}")
                
                case "bclear":
                    num = len(self.breakpoints)
                    self.breakpoints.clear() # clear the set
                    print(f"removed {num} breakpoint{'' if num == 1 else 's'}.")

                case "regs" | "r":
                    line_1 = "  ".join([f"{reg}:  0x{self.reg_get(REGISTERS.index(reg)):04X}" for reg in REGISTERS])
                    line_2 = f"PC: 0x{self.pc.value:04X}  SP: 0x{self.sp.value:04X}  MB: 0x{self.mb.value:04X}  Z:  0x{self.z.value:04X}"
                    print(line_1, line_2, sep="\n")

                case "flags" | "f":
                    print(f"C: {self.flag_get(FLAG_C)}  Z: {self.flag_get(FLAG_Z)}  N: {self.flag_get(FLAG_N)}  O: {self.flag_get(FLAG_O)}      I: {self.flag_get(FLAG_I)}")
                
                case "set":
                    if not assert_num_args(2, opt=0): continue # noqa: E701
                    value = parse_integer(1, base=16)
                    if value < 0 or value > 0xFFFF:
                        logger.error("invalid value for 16-bit integer.")
                        continue
                    reg = args[0].upper()
                    if reg not in REGISTERS:
                        if reg == "PC": self.pc.set(value) # noqa: E701
                        elif reg == "SP": self.sp.set(value) # noqa: E701
                        elif reg == "MB": self.mb.set(value) # noqa: E701
                        elif reg == "Z": self.z.set(value) # noqa: E701
                        else: logger.error(f"invalid register (expected one of {', '.join(REGISTERS)}, PC, SP, MB, ST, Z).") # noqa: E701
                    else:
                        self.reg_set(REGISTERS.index(reg), value)
                    print(f"set register {reg} to 0x{value:04X}.")
                
                case "mem" | "m":
                    if not assert_num_args(1, opt=1): continue # noqa: E701
                    addr = self.pc.value if args[0].upper() == "PC" else parse_integer(0, base=16)
                    length = parse_integer(1, default=16) * 2
                    chunk = self.memory[addr:addr+length]
                    for i in range(0, len(chunk), 32):
                        row = chunk[i:i+32]
                        words: list[int] = [(row[i] | row[i+1] << 8) for i in range(0, len(row), 2)]
                        print(f"0x{addr+i:04X} | {" ".join([f"{w:04X}" for w in words])} | {''.join(chr(w) if 0x20 <= w <= 0x7E else '.' for w in words)}")
                
                case "disasm" | "d":
                    if not assert_num_args(0, opt=1): continue # noqa: E701
                    addr = parse_integer(0, base=16, default=self.pc.value)
                    print(disasm_at(addr))
                
                case "ports":
                    non_zero = [i for i in range(len(self.ports)) if self.ports[i] != 0]
                    if len(non_zero) == 0: print("no non-zero ports found.") # noqa: E701
                    for i in non_zero:
                        print(f"port {i}: 0x{self.ports[i]:02X}")
                
                case "clear":
                    os.system("cls" if os.name == "nt" else "clear")
                
                case "help":
                    print("jaide emulator shell version 0.0.3 command list")
                    print(help_string("load", "<path> [addr]", "load a binary file into memory"))
                    print(help_string("dev", "<name>", "initialize a device"))
                    print(help_string("run", "", "execute until until a breakpoint or halt"))
                    print(help_string("step", "", "execute one instruction"))
                    print(help_string("break", "<addr>", "set a breakpoint at the given addrezss"))
                    print(help_string("blist", "", "list all breakpoints"))
                    print(help_string("bclear", "", "clear all breakpoints"))
                    print(help_string("regs", "", "display register values"))
                    print(help_string("flags", "", "display flag values"))
                    print(help_string("set", "<reg> <value>", "set the value of a register"))
                    print(help_string("mem", "<addr/pc> <len>", "display memory contents at addr (or pc)"))
                    print(help_string("disasm", "[addr]", "disassemble instruction at address (or pc)"))
                    print(help_string("ports", "", "display non-zero port values"))
                    print(help_string("help", "", "show this message"))
                    print(help_string("clear", "", "clear the screen"))
                    print(help_string("quit", "", "exit the emulator"))
                
                case ":3":
                    print(":3")
                
                case "q" | "quit" | "exit":
                    print("bye!")
                    break
                
                case _:
                    print("invalid command. type 'help' for a list of commands.")


    def assert_addressing_mode(self, actual: int, expected: int | list[int]) -> None:
        if isinstance(expected, int):
            expected = [expected]
        if actual not in expected:
            expected_string = "any of " + ", ".join([str(m) for m in expected]) if len(expected) > 1 else str(expected[0])
            raise EmulatorException(f"invalid addressing mode {actual} at 0x{self.pc:04X} (expected {expected_string}, got {actual}: {actual:08b}).")

    def get_mode(self, decoded: tuple[int, ...]) -> int:
        # decoded is always a tuple of (opcode, mode, *operands)
        return decoded[1]


    # operation handlers

    def handle_halt(self, decoded: tuple[int, ...]) -> None: self.halted = True

    def handle_load(self, decoded: tuple[int, ...]) -> str | None: pass

    def handle_store(self, decoded: tuple[int, ...]) -> str | None: pass
    
    def handle_move(self, decoded: tuple[int, ...]) -> None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: RA <- RB
        # MODE_IMM16: RA <- IMM16
        print(f"MOV {REGISTERS[reg_a]} <- {imm16} at 0x{self.pc}")
        if mode == MODE_REG:
            self.reg_set(reg_a, self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            self.reg_set(reg_a, imm16)
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for MOV at 0x{self.pc:04X}.")

    def handle_push(self, decoded: tuple[int, ...]) -> None: pass
    
    def handle_pop(self, decoded: tuple[int, ...]) -> None: pass

    def handle_add(self, decoded: tuple[int, ...]) -> None: pass

    def handle_adc(self, decoded: tuple[int, ...]) -> None: pass

    def handle_sub(self, decoded: tuple[int, ...]) -> None: pass

    def handle_sbc(self, decoded: tuple[int, ...]) -> None: pass

    def handle_inc(self, decoded: tuple[int, ...]) -> None: pass

    def handle_dec(self, decoded: tuple[int, ...]) -> None: pass

    def handle_shl(self, decoded: tuple[int, ...]) -> None: pass

    def handle_shr(self, decoded: tuple[int, ...]) -> None: pass

    def handle_and(self, decoded: tuple[int, ...]) -> None: pass

    def handle_or(self, decoded: tuple[int, ...]) -> None: pass

    #TODO: should z, n, flags be set for boolean operations?

    def handle_nor(self, decoded: tuple[int, ...]) -> None: pass

    def handle_not(self, decoded: tuple[int, ...]) -> None: pass

    def handle_xor(self, decoded: tuple[int, ...]) -> None: pass

    def handle_inb(self, decoded: tuple[int, ...]) -> None: pass
    
    def handle_outb(self, decoded: tuple[int, ...]) -> str | None:
        _, mode, reg_a, reg_b, imm16 = decoded
        # MODE_REG: port(RA) <- RB
        # MODE_IMM16: port(IMM16) <- RB
        print(f"OUTB {imm16} <- {self.reg_get(reg_b)}")
        if mode == MODE_REG:
            self.port_set(self.reg_get(reg_a), self.reg_get(reg_b))
        elif mode == MODE_IMM16:
            self.port_set(imm16, self.reg_get(reg_b))
        else:
            raise EmulatorException(f"invalid addressing mode {mode} for OUTB at 0x{self.pc:04X}.")

    def handle_cmp(self, decoded: tuple[int, ...]) -> None: pass

    def handle_jmp(self, decoded: tuple[int, ...]) -> None: pass

    def handle_jz(self, decoded: tuple[int, ...]) -> None: pass

    def handle_jnz(self, decoded: tuple[int, ...]) -> None: pass

    def handle_jc(self, decoded: tuple[int, ...]) -> None: pass

    def handle_jnc(self, decoded: tuple[int, ...]) -> None: pass

    def handle_call(self, decoded: tuple[int, ...]) -> None: pass

    def handle_ret(self, decoded: tuple[int, ...]) -> None: pass

    def handle_int(self, decoded: tuple[int, ...]) -> None: pass

    def handle_iret(self, decoded: tuple[int, ...]) -> None: pass

    def handle_nop(self, decoded: tuple[int, ...]) -> None: pass

    def _populate_handlers(self) -> None:
        self.handlers[OP_HALT]  = self.handle_halt
        self.handlers[OP_LOAD]  = self.handle_load
        self.handlers[OP_STORE] = self.handle_store
        self.handlers[OP_MOVE]  = self.handle_move
        self.handlers[OP_PUSH]  = self.handle_push
        self.handlers[OP_POP]   = self.handle_pop
        self.handlers[OP_ADD]   = self.handle_add
        self.handlers[OP_ADC]   = self.handle_adc
        self.handlers[OP_SUB]   = self.handle_sub
        self.handlers[OP_SBC]   = self.handle_sbc
        self.handlers[OP_INC]   = self.handle_inc
        self.handlers[OP_DEC]   = self.handle_dec
        self.handlers[OP_SHL]   = self.handle_shl
        self.handlers[OP_SHR]   = self.handle_shr
        self.handlers[OP_AND]   = self.handle_and
        self.handlers[OP_OR]    = self.handle_or
        self.handlers[OP_NOR]   = self.handle_nor
        self.handlers[OP_NOT]   = self.handle_not
        self.handlers[OP_XOR]   = self.handle_xor
        self.handlers[OP_INB]   = self.handle_inb
        self.handlers[OP_OUTB]  = self.handle_outb
        self.handlers[OP_CMP]   = self.handle_cmp
        self.handlers[OP_JMP]   = self.handle_jmp
        self.handlers[OP_JZ]    = self.handle_jz
        self.handlers[OP_JNZ]   = self.handle_jnz
        self.handlers[OP_JC]    = self.handle_jc
        self.handlers[OP_JNC]   = self.handle_jnc
        self.handlers[OP_CALL]  = self.handle_call
        self.handlers[OP_RET]   = self.handle_ret
        self.handlers[OP_INT]   = self.handle_int
        self.handlers[OP_IRET]  = self.handle_iret
        self.handlers[OP_NOP]   = self.handle_nop
