# repl.py
# read-eval-print loop for the jaide emulator.
# josiah bergen, february 2026

import os
import shlex
from collections.abc import Callable
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event, Thread

import pygame
from colorama import Fore as f

from common.isa import OPCODE_FORMATS
from jaide.constants import FLAG_C, FLAG_N, FLAG_O, FLAG_Z, REGISTERS
from jaide.devices.graphics import FRAME_INTERVAL, Graphics
from jaide.emulator import Emulator
from jaide.exceptions import EmulatorException, ReplException
from jaide.util.logger import logger


def parse_hex16(value: str) -> int:
    number = int(value, 16)
    if not 0 <= number <= 0xFFFF:
        raise ValueError("expected a 16-bit hexadecimal value")
    return number


def parse_register(value: str) -> str:
    register = value.upper()
    if register not in REGISTERS:
        raise ValueError(f'unknown register "{value}"')
    return register


@dataclass(frozen=True)
class Arg:
    name: str
    parse_value: Callable[[str], object] = str

    def parse(self, value: str) -> object:
        try:
            return self.parse_value(value)
        except ValueError as error:
            message = str(error) or f'invalid value "{value}"'
            raise ReplException(f"invalid {self.name}: {message}.") from error

    def __str__(self) -> str:
        return f"<{self.name}>"


@dataclass(frozen=True)
class Command:
    name: str
    aliases: tuple[str, ...] = ()
    args: tuple[Arg, ...] = ()
    description: str = ""

    def parse(self, raw_args: list[str]) -> tuple[object, ...]:
        if len(raw_args) != len(self.args):
            raise ReplException(f"expected {len(self.args)} arguments, got {len(raw_args)}.")
        return tuple(arg.parse(value) for arg, value in zip(self.args, raw_args))

    def __str__(self) -> str:
        command = self.name + " " + " ".join(str(arg) for arg in self.args)
        return f"{command:<25} {self.description}"


COMMANDS = (
    Command("load", ("l",), (Arg("file"), Arg("addr", parse_hex16)), "load a binary file into memory"),
    Command("run", description="execute until a breakpoint or halt"),
    Command("step", ("s",), description="execute one instruction"),
    Command("break", ("b",), (Arg("addr", parse_hex16),), "set a breakpoint at the given address"),
    Command("blist", ("bl",), description="list all breakpoints"),
    Command("bclear", ("bc",), description="clear all breakpoints"),
    Command("regs", ("r",), description="display register values"),
    Command("flags", ("f",), description="display flag values"),
    Command("devices", ("dev",), description="display device values"),
    Command("set", args=(Arg("reg", parse_register), Arg("value", parse_hex16)), description="set a register value"),
    Command("mset", args=(Arg("addr", parse_hex16), Arg("value", parse_hex16)), description="set a memory value"),
    Command("mem", ("m",), (Arg("addr", parse_hex16), Arg("len", parse_hex16)), "display memory contents"),
    Command("disasm", ("d",), (Arg("addr", parse_hex16),), "disassemble an instruction"),
    Command("disasm_pc", ("dp",), description="disassemble the instruction at pc"),
    Command("vram", description="display the vram"),
    Command("mmio", description="list MMIO device registers"),
    Command("reset", description="reset the emulator"),
    Command("clear", description="clear the screen"),
    Command("help", description="display help"),
    Command("quit", ("q", "exit"), description="exit the emulator"),
)

COMMAND_BY_NAME = {name: command for command in COMMANDS for name in (command.name, *command.aliases)}


@dataclass
class CommandRequest:
    name: str
    args: tuple[object, ...] = ()
    completed: Event = field(default_factory=Event, repr=False)


def split_line(line: str) -> list[str]:
    """Split a command line while preserving backslashes in Windows paths."""
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)


def parse_line(line: str) -> CommandRequest | None:
    try:
        words = split_line(line)
    except ValueError as error:
        raise ReplException(str(error)) from error

    if not words:
        return None

    name, *raw_args = words
    if name == ":3":
        return CommandRequest(name)

    command = COMMAND_BY_NAME.get(name)
    if command is None:
        raise ReplException(f"unknown command: {name}.")

    return CommandRequest(command.name, command.parse(raw_args))


class REPL:
    """Own terminal input and submit parsed commands to the main thread."""

    def __init__(self, requests: Queue[CommandRequest]):
        self.requests = requests

    def run(self) -> None:
        logger.info("jaide shell version 0.0.3")
        logger.info("welcome to the emulator! type 'help' for a list of commands.")

        while True:
            try:
                line = input(f"{f.WHITE}jaide > {f.RESET}")
                request = parse_line(line)
            except EOFError:
                request = CommandRequest("quit")
            except ReplException as error:
                logger.error(str(error))
                continue

            if request is None:
                continue

            self.requests.put(request)
            request.completed.wait()

            if request.name == "quit":
                return


def run_interactive(emulator: Emulator) -> None:
    """Run terminal input off-thread while the main thread services Pygame."""
    requests: Queue[CommandRequest] = Queue()
    repl = REPL(requests)
    repl_thread = Thread(target=repl.run, name="jaide-repl", daemon=True)
    repl_thread.start()

    graphics = next((device for device in emulator.devices if isinstance(device, Graphics)), None)

    try:
        while True:
            if graphics is not None:
                graphics.tick()

            try:
                request = requests.get(timeout=FRAME_INTERVAL / 2)
            except Empty:
                continue

            try:
                if request.name == "quit":
                    logger.info("bye!")
                    return
                execute_command(emulator, request)
            except (EmulatorException, ReplException, ValueError) as error:
                logger.error(f"{request.name}: {error}")
            finally:
                request.completed.set()
    finally:
        if graphics is not None:
            pygame.quit()


def disasm_at(emulator: Emulator, addr: int) -> str:
    word = emulator.bus.peek16(addr)
    regs, opcode = word & 0xFF, (word >> 8) & 0xFF
    reg_a = (regs >> 4) & 0xF
    reg_b = regs & 0xF

    if opcode not in OPCODE_FORMATS:
        return f"??? (unknown opcode 0x{opcode:02x})"

    fmt = OPCODE_FORMATS[opcode]
    imm16 = emulator.bus.peek16(addr + 1) if fmt.imm_operand is not None else 0
    reg_a_str = f" {REGISTERS[reg_a]}" if fmt.src_operand is not None else ""
    reg_b_str = f" {REGISTERS[reg_b]}" if fmt.dest_operand is not None else ""
    imm16_str = f" {imm16:04X}" if fmt.imm_operand is not None else ""
    return f"{fmt.mnemonic.name}{reg_a_str}{reg_b_str}{imm16_str}"


def display_memory(emulator: Emulator, word_addr: int, length_words: int) -> None:
    words = [emulator.bus.peek16(word_addr + offset) for offset in range(length_words)]
    for word_offset in range(0, len(words), 16):
        row = words[word_offset : word_offset + 16]
        values = " ".join(f"{word:04X}" for word in row)
        text = "".join(chr(word) if 0x20 <= word <= 0x7E else "." for word in row)
        logger.info(f"0x{word_addr + word_offset:04X} | {values} | {text}")


def execute_command(emulator: Emulator, request: CommandRequest) -> None:
    """Execute a parsed command. This is called only by the main thread."""
    match request.name:
        case ":3":
            logger.info(":3")
        case "load":
            file, addr = request.args
            emulator.load_binary(file, addr)
        case "run":
            emulator.run()
        case "step":
            try:
                emulator.step()
            except EmulatorException as error:
                logger.error(f"emulator stopped: {error.message}")
        case "break":
            (addr,) = request.args
            emulator.breakpoints.add(addr)
            logger.info(f"set breakpoint at address 0x{addr:04X}.")
        case "blist":
            count = len(emulator.breakpoints)
            logger.info(f"found {count} breakpoint{'' if count == 1 else 's'}{':' if count else '.'}")
            for addr in emulator.breakpoints:
                logger.info(f"0x{addr:04X}: {disasm_at(emulator, addr)}")
        case "bclear":
            count = len(emulator.breakpoints)
            emulator.breakpoints.clear()
            logger.info(f"removed {count} breakpoint{'' if count == 1 else 's'}.")
        case "regs":
            general = "  ".join(f"{reg}:  0x{emulator.reg_get(REGISTERS.index(reg)):04X}" for reg in REGISTERS[:8])
            special = f"PC: 0x{emulator.pc.value:04X}  SP: 0x{emulator.sp.value:04X}  MB: 0x{emulator.mb.value:04X}  F:  0x{emulator.f.value:04X}"
            logger.info(f"{general}\n{special}")
        case "flags":
            logger.info(f"C: {emulator.flag_get(FLAG_C)}  Z: {emulator.flag_get(FLAG_Z)}  N: {emulator.flag_get(FLAG_N)}  O: {emulator.flag_get(FLAG_O)}")
        case "devices" | "mmio":
            if not emulator.devices:
                logger.info("no devices registered.")
            for device in emulator.devices:
                logger.info(str(device))
        case "set":
            reg, value = request.args
            emulator.reg_set(REGISTERS.index(reg), value)
            logger.info(f"set register {reg} to 0x{value:04X}.")
        case "mset":
            addr, value = request.args
            emulator.bus.write16(addr, value)
            logger.info(f"set memory at 0x{addr:04X} to 0x{value:04X}.")
        case "mem":
            addr, length = request.args
            display_memory(emulator, addr, length)
        case "disasm":
            (addr,) = request.args
            logger.info(disasm_at(emulator, addr))
        case "disasm_pc":
            logger.info(disasm_at(emulator, emulator.pc.value))
        case "vram":
            display_memory(emulator, 0x4000, 16)
        case "reset":
            emulator.reset()
        case "clear":
            os.system("cls" if os.name == "nt" else "clear")
        case "help":
            for command in COMMANDS:
                logger.info(str(command))
        case _:
            raise ReplException(f"unhandled command: {request.name}.")
