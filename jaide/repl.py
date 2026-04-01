# repl.py
# read-eval-print loop for the jaide emulator.
# josiah bergen, february 2026

import os
from colorama import Fore as f
from enum import Enum
from typing import Callable

from jaide.emulator import Emulator, mask16
from jaide.exceptions import ReplException
from jaide.util.logger import logger

from common.isa import OPCODE_FORMATS
from jaide.constants import (
    REGISTERS, FLAG_C, FLAG_Z, FLAG_N, FLAG_O, FLAG_I,
)


class Arg:

    class Type(Enum):
        STRING = 0
        I10 = 1
        I16 = 2

    def __init__(self, name: str, type: Type = Type.STRING):
        self.name = name
        self.type = type

    def parse(self, val: str) -> int | str:
        if self.type == self.Type.STRING:
            return val

        # integer parsing
        base = 10 if self.type == self.Type.I10 else 16
        try:
            return int(val, base)
        except ValueError:
            # propagate to the caller, as this command cannot continue
            raise ReplException(f"invalid argument (expected {self.type.name.lower()}, got \"{val}\").") 

    def __str__(self):
        return f"<{self.name}>"


class Cmd:

    def __init__(self, func: Callable, names: list[str], args: list[Arg], description: str = ""):
        self.func: Callable = func

        if len(names) == 0:
            raise ReplException("command must have at least one name.")
        self.name: str = names[0]
        self.aliases: list[str] = names[1:]
        self.args: list[Arg] = args
        self.description: str = description

    def execute(self, args: list[str]):
        if len(args) != len(self.args):
            raise ReplException(f"invalid number of arguments for command {self.name} (expected {len(self.args)}, got {len(args)}).")
        
        parsed_args = [a.parse(args[i]) for i,a in enumerate[Arg](self.args)]
        self.func(*parsed_args)

    def __str__(self):
         cmd_string = self.name + " " + " ".join([f"{arg}" for arg in self.args])
         return f"{cmd_string:<25} {self.description}"


class REPL:

    def __init__(self, emulator: Emulator):
        
        logger.info("jaide emulator shell version 0.0.3")
        logger.info("welcome to the emulator! type 'help' for a list of commands.")

        self.emulator: Emulator = emulator
        self.commands: list[Cmd] = []

        command_defs = [
            (self.c_load,   ["load" , "l"],   [("file", Arg.Type.STRING), ("addr", Arg.Type.I16)],"load a binary file into memory"),
            (self.c_run,    ["run"],          [], "execute until until a breakpoint or halt"),
            (self.c_step,   ["step", "s"],    [], "execute one instruction"),
            (self.c_break,  ["break", "b"],   [("addr", Arg.Type.I16)], "set a breakpoint at the given addrezss"),
            (self.c_blist,  ["blist", "bl"],  [], "list all breakpoints"),
            (self.c_bclear, ["bclear", "bc"], [], "clear all breakpoints"),
            (self.c_regs,   ["regs", "r"],    [], "display register values"),
            (self.c_flags,  ["flags", "f"],   [], "display flag values"),
            (self.c_set,    ["set"],          [("reg", Arg.Type.STRING), ("value", Arg.Type.I16)], "set the value of a register"),
            (self.c_mset,   ["mset"],         [("addr", Arg.Type.I16), ("value", Arg.Type.I16)], "set the value of memory at the given address"),
            (self.c_mem,    ["mem", "m"],     [("addr", Arg.Type.I16), ("len", Arg.Type.I16)], "display memory contents at addr or pc"),
            (self.c_disasm, ["disasm", "d"],  [("addr", Arg.Type.I16)], "disassemble instruction at address (pc if no address provided)"),
            (self.c_disasm_pc, ["disasm_pc", "dp"],  [], "disassemble instruction at pc"),
            (self.c_vram,   ["vram"],        [], "display the vram"),
            (self.c_ports,  ["ports"],        [], "display non-zero port values"),
            (self.c_reset,  ["reset"],        [], "reset the emulator"),
            (self.c_clear,  ["clear"],        [], "clear the screen"),
            (self.c_help,   ["help"],         [], "display help"),
        ]

        for func, names, args, description in command_defs:
            self.commands.append(Cmd(func, names, [Arg(*a) for a in args], description))
                
        while True:
            try:
                name, *args = input(f"{f.LIGHTWHITE_EX}jaide > {f.RESET}").split()
            except KeyboardInterrupt:
                raise # let it propagate to __main__.py
            except (EOFError, ValueError):
                continue # empty/EOF input

            if name in ["q", "quit", "exit"]:
                logger.info("bye!")
                self.emulator.shutdown()

            if self.special_command(name):
                continue

            for cmd in self.commands:
                if name == cmd.name or name in cmd.aliases:
                    try:
                        cmd.execute(args)
                    except ReplException as e:
                        logger.error(f"{name}: {e}")
                    break
            else:
                logger.info(f"invalid command: {name}")

    def special_command(self, name: str) -> bool:
        match name:
            case ":3":
                logger.info(":3")
                return True
            case _:
                return False

    def disasm_at(self, addr: int) -> str:
        word  = self.emulator.read16(addr)
        regs, instr = self.emulator.split_word(word)
        opcode = instr
        reg_a  = (regs >> 4) & 0xF
        reg_b  = regs & 0xF

        if opcode not in OPCODE_FORMATS:
            return f"??? (unknown opcode 0x{opcode:02x})"

        fmt   = OPCODE_FORMATS[opcode]
        imm16 = self.emulator.read16(addr + 1) if fmt.imm_operand is not None else 0

        reg_a_str = f" {REGISTERS[reg_a]}" if fmt.src_operand is not None else ''
        reg_b_str = f" {REGISTERS[reg_b]}" if fmt.dest_operand is not None else ''
        imm16_str = f" {imm16:04X}"        if fmt.imm_operand is not None else ''
        return f"{fmt.mnemonic.name}{reg_a_str}{reg_b_str}{imm16_str}"

    def c_load(self, file: str, addr: int):
        self.emulator.load_binary(file, addr)

    def c_run(self):
        self.emulator.halted = False
        self.emulator.run()

    def c_step(self):
        self.emulator.step()

    def c_break(self, addr: int):
        self.emulator.breakpoints.add(addr)
        logger.info(f"set breakpoint at address 0x{addr:04X}.")

    def c_blist(self):
        num = len(self.emulator.breakpoints)
        logger.info(f"found {num} breakpoint{'' if num == 1 else 's'}{':' if num > 0 else '.'}")
        for addr in self.emulator.breakpoints:
            logger.info(f"0x{addr:04X}: {self.disasm_at(addr)}")

    def c_bclear(self):
        num = len(self.emulator.breakpoints)
        self.emulator.breakpoints.clear() # clear the set
        logger.info(f"removed {num} breakpoint{'' if num == 1 else 's'}.")
        
    def c_regs(self):
        line_1 = "  ".join([f"{reg}:  0x{self.emulator.reg_get(REGISTERS.index(reg)):04X}" for reg in REGISTERS[:8]])
        line_2 = f"PC: 0x{self.emulator.pc.value:04X}  SP: 0x{self.emulator.sp.value:04X}  MB: 0x{self.emulator.mb.value:04X}  F:  0x{self.emulator.f.value:04X}"
        logger.info(f"{line_1}\n{line_2}")  # all addresses displayed as word addresses

    def c_flags(self):
        line_1 = f"C: {self.emulator.flag_get(FLAG_C)}  Z: {self.emulator.flag_get(FLAG_Z)}  N: {self.emulator.flag_get(FLAG_N)}  O: {self.emulator.flag_get(FLAG_O)}  I: {self.emulator.flag_get(FLAG_I)}"
        logger.info(line_1)

    def c_set(self, reg: str, value: int):
        self.emulator.reg_set(REGISTERS.index(reg), value)
        logger.info(f"set register {reg} to 0x{mask16(value):04X}.")

    def c_mset(self, addr: int, value: int):
        self.emulator.write16(addr, value)
        logger.info(f"set memory at 0x{addr:04X} to 0x{value:04X}.")

    def c_mem(self, word_addr: int, length_words: int):
        byte_addr = word_addr * 2  # convert word address to byte address for memory array access
        length_bytes = length_words * 2
        chunk = self.emulator.memory[byte_addr:byte_addr+length_bytes]
        for i in range(0, len(chunk), 32):
            row = chunk[i:i+32]
            words: list[int] = [(row[j] | row[j+1] << 8) for j in range(0, len(row), 2)]
            word_offset = i // 2  # convert byte offset to word offset
            logger.info(f"0x{word_addr+word_offset:04X} | {" ".join([f"{w:04X}" for w in words])} | {''.join(chr(w) if 0x20 <= w <= 0x7E else '.' for w in words)}")

    def c_disasm(self, addr: int):
        logger.info(self.disasm_at(addr))

    def c_disasm_pc(self):
        logger.info(self.disasm_at(self.emulator.pc.value))

    def c_vram(self):
        chunk = self.emulator.vram[:32]
        for i in range(0, len(chunk), 32):
            for i in range(0, len(chunk), 32):
                row = chunk[i:i+32]
                words: list[int] = [(row[j] | row[j+1] << 8) for j in range(0, len(row), 2)]
                word_offset = i // 2  # convert byte offset to word offset
                logger.info(f"0x{word_offset:04X} | {" ".join([f"{w:04X}" for w in words])} | {''.join(chr(w) if 0x20 <= w <= 0x7E else '.' for w in words)}")

    def c_ports(self):
        non_zero = [i for i in range(len(self.emulator.ports)) if self.emulator.ports[i] != 0]
        if len(non_zero) == 0:
            logger.info("no non-zero ports found.")
            return
        for i in non_zero:
            logger.info(f"port {i}: 0x{self.emulator.ports[i]:02X}")

    def c_clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def c_help(self):
        for cmd in self.commands:
            logger.info(str(cmd))

    def c_reset(self):
        self.emulator.reset()