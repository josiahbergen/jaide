# repl.py
# read-eval-print loop for the jaide emulator.
# josiah bergen, february 2026

import os
from colorama import Fore as f

from jaide.emulator import Emulator
from jaide.util.logger import logger

from jaide.constants import (
    MNEMONICS, INSTRUCTION_ENCODINGS,
    MODE_IMM16, MODE_MEM_DIRECT,
    REGISTERS, LOC, FLAG_C, FLAG_Z, FLAG_N, FLAG_O, FLAG_I,
)

class REPL:

    def __init__(self, emulator: Emulator):
        scope = "repl.py:REPL()"
        
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
            word = emulator.read16(addr)
            regs, instr = emulator.split_word(word)
            opcode, mode, reg_a, reg_b, imm16 = (instr >> 2) & 0b111111, instr & 0b11, (regs >> 4) & 0b1111, regs & 0b1111, 0

            if mode not in INSTRUCTION_ENCODINGS[opcode]:
                return f"{MNEMONICS[opcode]} {mode:02X} (invalid addressing mode)"
            if mode in [MODE_IMM16, MODE_MEM_DIRECT]:
                imm16 = emulator.read16(addr + 1)

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
                    emulator.load_binary(file, addr)
                
                case "run":
                    emulator.halted = False
                    emulator.run()
    
                case "step" | "s":
                    emulator.halted = False
                    res = emulator.step()
                    if res: print(res) # noqa: E701
                
                case "break" | "b":
                    if not assert_num_args(1, opt=0): continue # noqa: E701
                    addr = parse_integer(0, base=16)
                    emulator.breakpoints.add(addr)
                    print(f"set breakpoint at address 0x{addr:04X}.")
                
                case "blist" | "bl":
                    num = len(emulator.breakpoints)
                    print(f"found {num} breakpoint{'' if num == 1 else 's'}{':' if num > 0 else '.'}")
                    for addr in emulator.breakpoints:
                        print(f"0x{addr:04X}: {disasm_at(addr)}")
                
                case "bclear" | "bc":
                    num = len(emulator.breakpoints)
                    emulator.breakpoints.clear() # clear the set
                    print(f"removed {num} breakpoint{'' if num == 1 else 's'}.")

                case "regs" | "r":
                    line_1 = "  ".join([f"{reg}:  0x{emulator.reg_get(REGISTERS.index(reg)):04X}" for reg in REGISTERS[:8]])
                    line_2 = f"PC: 0x{emulator.pc.value:04X}  SP: 0x{emulator.sp.value:04X}  MB: 0x{emulator.mb.value:04X}  F: 0x{emulator.f.value:04X}"
                    print(line_1, line_2, sep="\n")  # All addresses displayed as word addresses

                case "flags" | "f":
                    print(f"C: {emulator.flag_get(FLAG_C)}  Z: {emulator.flag_get(FLAG_Z)}  N: {emulator.flag_get(FLAG_N)}  O: {emulator.flag_get(FLAG_O)}  I: {emulator.flag_get(FLAG_I)}")
                
                case "set":
                    if not assert_num_args(2, opt=0): continue # noqa: E701
                    value = parse_integer(1, base=16)
                    if value < 0 or value > 0xFFFF:
                        logger.error("invalid value for 16-bit integer.")
                        continue
                    reg = args[0].upper()
                    emulator.reg_set(REGISTERS.index(reg), value)
                    print(f"set register {reg} to 0x{value:04X}.")

                case "mset":
                    if not assert_num_args(2, opt=0): continue # noqa: E701
                    addr = parse_integer(0, base=16)
                    value = parse_integer(1, base=16)
                    emulator.write16(addr, value)
                    print(f"set memory at 0x{addr:04X} to 0x{value:04X}.")
                
                case "mem" | "m":
                    if not assert_num_args(1, opt=1): continue # noqa: E701
                    # Accept word address from user
                    word_addr = emulator.pc.value if args[0].upper() == "PC" else parse_integer(0, base=16)
                    byte_addr = word_addr * 2  # convert word address to byte address for memory array access
                    length_words = parse_integer(1, default=16)
                    length_bytes = length_words * 2
                    chunk = emulator.memory[byte_addr:byte_addr+length_bytes]
                    for i in range(0, len(chunk), 32):
                        row = chunk[i:i+32]
                        words: list[int] = [(row[j] | row[j+1] << 8) for j in range(0, len(row), 2)]
                        word_offset = i // 2  # convert byte offset to word offset
                        print(f"0x{word_addr+word_offset:04X} | {" ".join([f"{w:04X}" for w in words])} | {''.join(chr(w) if 0x20 <= w <= 0x7E else '.' for w in words)}")
                
                case "disasm" | "d":
                    if not assert_num_args(0, opt=1): continue # noqa: E701
                    addr = parse_integer(0, base=16, default=emulator.pc.value)
                    print(disasm_at(addr))
                
                case "ports":
                    non_zero = [i for i in range(len(emulator.ports)) if emulator.ports[i] != 0]
                    if len(non_zero) == 0: print("no non-zero ports found.") # noqa: E701
                    for i in non_zero:
                        print(f"port {i}: 0x{emulator.ports[i]:02X}")
                
                case "clear":
                    os.system("cls" if os.name == "nt" else "clear")

                case "vram":
                    for i in range(0, 1000, 32): # only display first 1000 words of vram
                        row = emulator.vram[i:i+32]
                        words = [(row[j] | row[j+1] << 8) for j in range(0, len(row), 2)]
                        print(f"0x{i // 2:04X} | {" ".join([f"{w:04X}" for w in words])} | {''.join(chr(w) if 0x20 <= w <= 0x7E else '.' for w in words)}")
                
                case "help":
                    print("jaide emulator shell version 0.0.3 command list")
                    print(help_string("load", "<path> [addr]", "load a binary file into memory"))
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

