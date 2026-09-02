import shlex
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event, Thread

import pygame
from colorama import Fore as f

from common.isa import OPCODE_FORMATS
from emulator.constants import FLAG_C, FLAG_N, FLAG_O, FLAG_Z, REGISTERS
from emulator.devices.graphics import FRAME_INTERVAL, Graphics
from emulator.emulator import Emulator
from emulator.exceptions import EmulatorException
from emulator.util.disasm import disassemble
from emulator.util.logger import logger


def hex16(value: str) -> int:
    try:
        number = int(value, 16)
    except ValueError:
        raise ValueError(f'expected a hexadecimal value, got "{value}"') from None
    if not 0 <= number <= 0xFFFF:
        raise ValueError(f'expected a 16-bit value, got "{value}"')
    return number


def arguments(values: list[str], *parsers):
    if len(values) != len(parsers):
        raise ValueError(f"expected {len(parsers)} arguments, got {len(values)}")
    return tuple(parser(value) for parser, value in zip(parsers, values))


def split_line(line: str) -> list[str]:
    """Split a command line while preserving backslashes in Windows paths."""
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)


@dataclass
class CommandRequest:
    name: str
    args: list[str]
    completed: Event = field(default_factory=Event, repr=False)


def parse_line(line: str) -> CommandRequest | None:
    words = split_line(line)
    if not words:
        return None

    name, *args = words
    if name not in COMMANDS:
        raise ValueError(f"unknown command: {name}")
    return CommandRequest(name, args)


def disasm_at(emulator: Emulator, addr: int) -> str:
    word = emulator.bus.peek16(addr)
    regs, opcode = word & 0xFF, word >> 8
    fmt = OPCODE_FORMATS.get(opcode)
    imm16 = emulator.bus.peek16(addr + 1) if fmt and fmt.imm_operand is not None else 0
    return disassemble((opcode, regs >> 4, regs & 0xF, imm16))


def display_memory(emulator: Emulator, addr: int, length: int) -> None:
    words = [emulator.bus.peek16(addr + offset) for offset in range(length)]
    for offset in range(0, length, 16):
        row = words[offset : offset + 16]
        values = " ".join(f"{word:04X}" for word in row)
        text = "".join(chr(word) if 0x20 <= word <= 0x7E else "." for word in row)
        logger.info(f"0x{addr + offset:04X} | {values} | {text}")


def load(emulator: Emulator, args: list[str]) -> None:
    """load <file> <addr>       load a binary file into memory"""
    file, addr = arguments(args, str, hex16)
    emulator.load_binary(file, addr)


def run(emulator: Emulator, args: list[str]) -> None:
    """run                      execute until a breakpoint or halt"""
    arguments(args)
    emulator.run()


def step(emulator: Emulator, args: list[str]) -> None:
    """step                     execute one instruction"""
    arguments(args)
    emulator.step()


def breakpoint(emulator: Emulator, args: list[str]) -> None:
    """break [<addr>|clear]     list, set, or clear breakpoints"""
    if not args:
        for addr in sorted(emulator.breakpoints):
            logger.info(f"0x{addr:04X}: {disasm_at(emulator, addr)}")
        if not emulator.breakpoints:
            logger.info("no breakpoints set")
        return

    if args == ["clear"]:
        count = len(emulator.breakpoints)
        emulator.breakpoints.clear()
        logger.info(f"removed {count} breakpoint{'' if count == 1 else 's'}")
        return

    (addr,) = arguments(args, hex16)
    emulator.breakpoints.add(addr)
    logger.info(f"set breakpoint at 0x{addr:04X}")


def registers(emulator: Emulator, args: list[str]) -> None:
    """regs                     display registers and flags"""
    arguments(args)
    general = "  ".join(f"{reg}: 0x{emulator.reg_get(index):04X}" for index, reg in enumerate(REGISTERS[:8]))
    special = f"PC: 0x{emulator.pc.value:04X}  SP: 0x{emulator.sp.value:04X}  MB: 0x{emulator.mb.value:04X}  F: 0x{emulator.f.value:04X}"
    flags = f"C: {emulator.flag_get(FLAG_C)}  Z: {emulator.flag_get(FLAG_Z)}  N: {emulator.flag_get(FLAG_N)}  O: {emulator.flag_get(FLAG_O)}"
    logger.info(f"{general}\n{special}\n{flags}")


def devices(emulator: Emulator, args: list[str]) -> None:
    """devices                  display devices and MMIO registers"""
    arguments(args)
    if not emulator.devices:
        logger.info("no devices registered")
    for device in emulator.devices:
        logger.info(str(device))


def set_register(emulator: Emulator, args: list[str]) -> None:
    """set <reg> <value>        set a register value"""
    register, value = arguments(args, str, hex16)
    register = register.upper()
    if register not in REGISTERS:
        raise ValueError(f'unknown register "{register}"')
    emulator.reg_set(REGISTERS.index(register), value)
    logger.info(f"set {register} to 0x{value:04X}")


def set_memory(emulator: Emulator, args: list[str]) -> None:
    """mset <addr> <value>      set a memory value"""
    addr, value = arguments(args, hex16, hex16)
    emulator.bus.write16(addr, value)
    logger.info(f"set memory at 0x{addr:04X} to 0x{value:04X}")


def memory(emulator: Emulator, args: list[str]) -> None:
    """mem <addr> <length>      display memory contents"""
    addr, length = arguments(args, hex16, hex16)
    display_memory(emulator, addr, length)


def disasm(emulator: Emulator, args: list[str]) -> None:
    """disasm [<addr>]          disassemble at an address or the PC"""
    if len(args) > 1:
        raise ValueError(f"expected at most 1 argument, got {len(args)}")
    addr = hex16(args[0]) if args else emulator.pc.value
    logger.info(disasm_at(emulator, addr))


def reset(emulator: Emulator, args: list[str]) -> None:
    """reset                    reset the emulator"""
    arguments(args)
    emulator.reset()


def help_command(_emulator: Emulator, args: list[str]) -> None:
    """help                     display this help"""
    arguments(args)
    for handler in COMMANDS.values():
        logger.info(handler.__doc__)


def quit_command(_emulator: Emulator, _args: list[str]) -> None:
    """quit                     exit the emulator"""
    logger.info("bye!")


COMMANDS = {
    "load": load,
    "run": run,
    "step": step,
    "break": breakpoint,
    "regs": registers,
    "devices": devices,
    "set": set_register,
    "mset": set_memory,
    "mem": memory,
    "disasm": disasm,
    "reset": reset,
    "help": help_command,
    "quit": quit_command,
}


def read_commands(requests: Queue[CommandRequest]) -> None:
    logger.info("jaide emulator; type 'help' for a list of commands")

    while True:
        try:
            request = parse_line(input(f"{f.WHITE}jaide > {f.RESET}"))
        except EOFError:
            request = CommandRequest("quit", [])
        except ValueError as error:
            logger.error(str(error))
            continue

        if request is None:
            continue

        requests.put(request)
        request.completed.wait()
        if request.name == "quit":
            return


def run_interactive(emulator: Emulator) -> None:
    """Read terminal input off-thread while the main thread services Pygame."""
    requests: Queue[CommandRequest] = Queue()
    Thread(target=read_commands, args=(requests,), name="jaide-repl", daemon=True).start()
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
                COMMANDS[request.name](emulator, request.args)
                if request.name == "quit":
                    return
            except (EmulatorException, ValueError) as error:
                logger.error(f"{request.name}: {error}")
            finally:
                request.completed.set()
    finally:
        if graphics is not None:
            pygame.quit()
