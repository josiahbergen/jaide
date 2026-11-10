# handlers.py
# instruction handlers for the jaide emulator.
#
# there is one handler per opcode, already specialized to its addressing modes.
# handlers are registered against a row of the isa with @op, and build_dispatch()
# lays them out into a 256-entry table indexed by opcode.
#
# every handler takes (emu, a, b, imm):
#   a, b  the register fields of the instruction word: the registers of the first and second REG/PTR operands
#   imm   the immediate word (0 if the opcode has none)

import time
from typing import TYPE_CHECKING, Callable

from common.isa import IMM, ISA, PTR, REG, REGISTERS, Mode

from .constants import EVENT, FLAG_C, FLAG_N, FLAG_O, FLAG_Z, SUPERVISOR_MODE, USER_MODE
from .exceptions import DivisionByZeroFault, EmulatorException, InvalidInstructionFault, ProtectionFault

if TYPE_CHECKING:
    from .emulator import Emulator

type Handler = Callable[[Emulator, int, int, int], None]

_handlers: dict[tuple[str, tuple[Mode, ...]], Handler] = {}


def op(mnemonic: str, *modes: Mode) -> Callable[[Handler], Handler]:
    """ Register a handler for the opcode with this mnemonic and these operand modes. """
    def register(handler: Handler) -> Handler:
        assert (mnemonic, modes) not in _handlers, f"duplicate handler for {mnemonic} {modes}"
        _handlers[mnemonic, modes] = handler
        return handler
    return register


def build_dispatch() -> list[Handler]:
    """ Build the opcode -> handler table, checking that the handlers cover the isa exactly. """
    remaining = dict(_handlers)
    table: list[Handler] = [invalid_opcode] * 256
    for spec in ISA:
        handler = remaining.pop((spec.mnemonic, spec.modes), None)
        assert handler is not None, f"no handler for '{spec.signature}' (opcode 0x{spec.opcode:02x})"
        table[spec.opcode] = handler
    assert not remaining, f"handlers that match no opcode: {list(remaining)}"
    return table


def invalid_opcode(emu: "Emulator", a: int, b: int, imm: int) -> None:
    raise InvalidInstructionFault(f"invalid opcode at 0x{emu.instruction_address:04x}.")


# system

@op("nop")
def nop(emu, a, b, imm):
    pass


@op("halt")
def halt(emu, a, b, imm):
    emu.stopped = True  # stays halted until reset
    raise EmulatorException("halted")


@op("wait")
def wait(emu, a, b, imm):
    if emu.mode == USER_MODE:
        raise ProtectionFault("attempted to wait while in an unprivileged mode")

    # enable interrupts and begin waiting
    emu.ie = True
    emu.waiting = True
    emu._wait_time = time.perf_counter()
    emu._last_print = 0


@op("syscall")
def syscall(emu, a, b, imm):
    if emu.mode == SUPERVISOR_MODE:
        raise InvalidInstructionFault("attempted to syscall while already in supervisor mode")

    # enter supervisor mode, using the contents of register a as the event detail
    emu.enter_supervisor(EVENT.SYSCALL, emu.reg_get(REGISTERS.A), emu.pc.value)


@op("transfer")
def transfer(emu, a, b, imm):
    if emu.mode == USER_MODE:
        raise ProtectionFault("attempted to transfer while in an unprivileged mode")

    # Read and validate the complete frame before changing any CPU state.
    frame_sp = emu.sp.value
    frame = [emu.bus.read16(frame_sp + offset) for offset in range(7)]
    _kind, _detail, target_mode, target_mb, target_flags, target_sp, target_pc = frame

    if target_mode not in (SUPERVISOR_MODE, USER_MODE):
        raise ProtectionFault(f"attempted to transfer to an invalid mode: {target_mode}")
    if target_flags & ~0x000F:
        raise ProtectionFault(f"attempted to transfer with invalid flags: {target_flags}")
    if target_mb > 31:
        raise ProtectionFault(f"attempted to transfer to an invalid memory bank {target_mb}")

    if target_mode == USER_MODE:
        if not 0x7000 <= target_pc <= 0xAFFF:
            raise ProtectionFault(f"attempted to transfer to an invalid user address: {target_pc}")
        if not 0x7000 <= target_sp <= 0xAFFF:
            raise ProtectionFault(f"attempted to transfer to an invalid user stack pointer: {target_sp}")
        if target_mb != 0:
            raise ProtectionFault(f"attempted to transfer to an invalid user bank: {target_mb}")

    if target_mode == USER_MODE:
        # Save the supervisor stack pointer after consuming this frame.
        emu.ssp.set((frame_sp + 7) & 0xFFFF)

    # Restore the target context atomically, making the target mode visible last.
    emu.pc.set(target_pc)
    emu.sp.set(target_sp)
    emu.mb.set(target_mb)
    emu.f.set(target_flags)
    emu.waiting = False
    emu.ie = target_mode == USER_MODE
    emu.mode = target_mode


@op("stc")
def stc(emu, a, b, imm):
    emu.flag_set(FLAG_C, True)


@op("clc")
def clc(emu, a, b, imm):
    emu.flag_set(FLAG_C, False)


# registers and the stack

@op("mov", REG, REG)
def mov_reg(emu, a, b, imm):
    emu.reg_set(a, emu.reg_get(b))


@op("mov", REG, IMM)
def mov_imm(emu, a, b, imm):
    emu.reg_set(a, imm)


@op("swp", REG, REG)
def swp(emu, a, b, imm):
    first, second = emu.reg_get(a), emu.reg_get(b)
    emu.reg_set(a, second)
    emu.reg_set(b, first)


@op("push", REG)
def push_reg(emu, a, b, imm):
    emu._push_core(emu.reg_get(a))


@op("push", IMM)
def push_imm(emu, a, b, imm):
    emu._push_core(imm)


@op("pop", REG)
def pop(emu, a, b, imm):
    emu.reg_set(a, emu._pop_core())


# memory

@op("get", REG, PTR)
def get(emu, a, b, imm):
    # dest <- [pointer]
    emu.reg_set(a, emu.bus.read16(emu.reg_get(b)))


@op("put", PTR, REG)
def put_reg(emu, a, b, imm):
    # [pointer] <- src
    emu.bus.write16(emu.reg_get(a), emu.reg_get(b))


@op("put", PTR, IMM)
def put_imm(emu, a, b, imm):
    # [pointer] <- imm
    emu.bus.write16(emu.reg_get(a), imm)


@op("bcp", REG, REG, IMM)
def bcp(emu, a, b, imm):
    # copy imm words from the address in the second register to the address in the first
    dst, src = emu.reg_get(a), emu.reg_get(b)
    for i in range(imm):
        emu.bus.write16(dst + i, emu.bus.read16(src + i))


# arithmetic and logic
# these all compute dest <- f(dest, src), where src is either a register or an immediate.

def binary(mnemonic: str, compute: Callable[["Emulator", int, int], int]) -> None:
    """ Register the 'reg, reg' and 'reg, imm' forms of a two-operand instruction. """

    @op(mnemonic, REG, REG)
    def with_reg(emu, a, b, imm):
        emu.reg_set(a, compute(emu, emu.reg_get(a), emu.reg_get(b)))

    @op(mnemonic, REG, IMM)
    def with_imm(emu, a, b, imm):
        emu.reg_set(a, compute(emu, emu.reg_get(a), imm))


def mul(emu: "Emulator", dest: int, src: int) -> int:
    full = dest * src
    result = full & 0xFFFF
    emu.set_all_flags(result == 0, full > 0xFFFF, result & 0x8000 != 0, 0)
    return result


def div(emu: "Emulator", dest: int, src: int) -> int:
    if src == 0:
        raise DivisionByZeroFault(f"division by zero at 0x{emu.instruction_address:04x}.")
    result = (dest // src) & 0xFFFF
    emu.set_all_flags(result == 0, dest % src != 0, result & 0x8000 != 0, 0)
    return result


def mod(emu: "Emulator", dest: int, src: int) -> int:
    if src == 0:
        raise DivisionByZeroFault(f"division by zero at 0x{emu.instruction_address:04x}.")
    result = (dest % src) & 0xFFFF
    emu.set_all_flags(result == 0, 0, result & 0x8000 != 0, 0)
    return result


def logic(emu: "Emulator", result: int) -> int:
    # bitwise operations only touch the zero flag
    emu.flag_set(FLAG_Z, result == 0)
    return result


binary("add", lambda emu, dest, src: emu._add_core(dest, src))
binary("adc", lambda emu, dest, src: emu._add_core(dest, src, int(emu.flag_get(FLAG_C))))
binary("sub", lambda emu, dest, src: emu._sub_core(dest, src))
binary("sbc", lambda emu, dest, src: emu._sub_core(dest, src, int(emu.flag_get(FLAG_C))))
binary("mul", mul)
binary("div", div)
binary("mod", mod)
binary("and", lambda emu, dest, src: logic(emu, dest & src))
binary("or",  lambda emu, dest, src: logic(emu, dest | src))
binary("xor", lambda emu, dest, src: logic(emu, dest ^ src))
binary("lsh", lambda emu, dest, src: emu._lsh_core(dest, src))
binary("rsh", lambda emu, dest, src: emu._rsh_core(dest, src))
binary("asr", lambda emu, dest, src: emu._asr_core(dest, src))


@op("inc", REG)
def inc(emu, a, b, imm):
    emu.reg_set(a, emu._add_core(emu.reg_get(a), 1))


@op("dec", REG)
def dec(emu, a, b, imm):
    emu.reg_set(a, emu._sub_core(emu.reg_get(a), 1))


@op("not", REG)
def not_(emu, a, b, imm):
    emu.reg_set(a, logic(emu, ~emu.reg_get(a) & 0xFFFF))


@op("cmp", REG, REG)
def cmp_reg(emu, a, b, imm):
    # flags <- first - second
    emu._sub_core(emu.reg_get(a), emu.reg_get(b))


@op("cmp", REG, IMM)
def cmp_imm(emu, a, b, imm):
    emu._sub_core(emu.reg_get(a), imm)


# jumps and calls

def call_to(emu: "Emulator", target: int) -> None:
    emu._push_core(emu.pc.value)  # return address: the instruction after the call
    emu.call_stack.append((emu.instruction_address, emu.source_map.get_source(emu.instruction_address).split(" ")[0]))
    emu.pc.set(target)


@op("jmp", REG)
def jmp_reg(emu, a, b, imm):
    emu.pc.set(emu.reg_get(a))


@op("jmp", IMM)
def jmp_imm(emu, a, b, imm):
    emu.pc.set(imm)


@op("call", REG)
def call_reg(emu, a, b, imm):
    call_to(emu, emu.reg_get(a))


@op("call", IMM)
def call_imm(emu, a, b, imm):
    call_to(emu, imm)


@op("ret")
def ret(emu, a, b, imm):
    emu.call_stack.pop()
    emu.pc.set(emu._pop_core())


# conditional branches

def branch(mnemonic: str, taken: Callable[["Emulator"], bool]) -> None:
    """ Register a branch that jumps to its immediate address when the condition holds. """

    @op(mnemonic, IMM)
    def jump(emu, a, b, imm):
        if taken(emu):
            emu.pc.set(imm)


branch("jz",  lambda emu: emu.flag_get(FLAG_Z))
branch("jnz", lambda emu: not emu.flag_get(FLAG_Z))
branch("jc",  lambda emu: emu.flag_get(FLAG_C))
branch("jnc", lambda emu: not emu.flag_get(FLAG_C))
branch("ja",  lambda emu: emu.flag_get(FLAG_C) and not emu.flag_get(FLAG_Z))
branch("jae", lambda emu: emu.flag_get(FLAG_C) or emu.flag_get(FLAG_Z))
branch("jb",  lambda emu: not emu.flag_get(FLAG_C))
branch("jbe", lambda emu: not emu.flag_get(FLAG_C) or emu.flag_get(FLAG_Z))
branch("jg",  lambda emu: not emu.flag_get(FLAG_Z) and emu.flag_get(FLAG_N) == emu.flag_get(FLAG_O))
branch("jge", lambda emu: emu.flag_get(FLAG_N) == emu.flag_get(FLAG_O))
branch("jl",  lambda emu: emu.flag_get(FLAG_N) != emu.flag_get(FLAG_O))
branch("jle", lambda emu: emu.flag_get(FLAG_Z) or emu.flag_get(FLAG_N) != emu.flag_get(FLAG_O))
