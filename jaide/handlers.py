from typing import Callable

from common.isa import INSTRUCTIONS, MODES, OPCODE_FORMATS

from .constants import FLAG_C, FLAG_I, FLAG_N, FLAG_O, FLAG_Z
from .emulator import Emulator, mask16
from .exceptions import EmulatorException
from .util.logger import logger


def _cond_jump(emu: Emulator, condition: bool, decoded: tuple[int, ...]) -> None:
    if condition:
        _, _, _, imm16 = decoded
        emu.pc.set(_jump_target(emu, imm16))


def _jump_target(emu: Emulator, imm16: int) -> int:
    """ Compute absolute jump target from a signed relative offset. """
    return mask16(emu.pc.value + emu._signed16(imm16))

# operation handlers
# decoded is always (opcode, reg_a, reg_b, imm16)
# reg_a = ssss (high nibble), reg_b = dddd (low nibble)
# see OPCODE_FORMATS for which operand each field represents per opcode.


def handle_halt(emu, _decoded: tuple[int, ...]) -> None:
    emu.waiting_for_interrupt = True


def handle_get(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    # reg_a = ssss = src ptr register, reg_b = dddd = dest register
    if modes == (MODES.REG, MODES.REG_POINTER):
        # dest <- [src_ptr]
        emu.reg_set(reg_b, emu.read16(emu.reg_get(reg_a)))
    elif modes == (MODES.REG, MODES.REL_POINTER):
        # dest <- [pc + offset]  (imm16 is signed offset to label)
        addr = mask16(emu.pc.value + emu._signed16(imm16))
        emu.reg_set(reg_b, emu.read16(addr))
    elif modes == (MODES.REG, MODES.OFF_POINTER):
        # dest <- [label + ptr_reg]  (imm16 is signed offset to base label)
        base = mask16(emu.pc.value + emu._signed16(imm16))
        emu.reg_set(reg_b, emu.read16(mask16(base + emu.reg_get(reg_a))))
    else:
        raise EmulatorException(f"unexpected GET variant at 0x{emu.pc.value:04x}.")


def handle_put(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    # reg_a = ssss = src register, reg_b = dddd = dest ptr register
    if modes == (MODES.REG_POINTER, MODES.REG):
        # [dest_ptr] <- src
        emu.write16(emu.reg_get(reg_b), emu.reg_get(reg_a))
    elif modes == (MODES.OFF_POINTER, MODES.REG):
        # [label + dest_ptr] <- src
        base = mask16(emu.pc.value + emu._signed16(imm16))
        emu.write16(mask16(base + emu.reg_get(reg_b)), emu.reg_get(reg_a))
    elif modes == (MODES.REL_POINTER, MODES.REG):
        # [pc + imm] <- src  (position-independent store to label)
        addr = mask16(emu.pc.value + emu._signed16(imm16))
        emu.write16(addr, emu.reg_get(reg_a))
    elif modes == (MODES.REG_POINTER, MODES.IMM):
        # [dest_ptr] <- imm  (dddd = dest ptr reg, imm = value)
        emu.write16(emu.reg_get(reg_b), imm16)
    else:
        raise EmulatorException(f"unexpected PUT variant at 0x{emu.pc.value:04x}.")


def handle_mov(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        # dest(reg_b) <- src(reg_a)
        emu.reg_set(reg_b, emu.reg_get(reg_a))
    elif modes == (MODES.REG, MODES.IMM):
        # dest(reg_a) <- imm  [dest is in ssss slot for imm variants]
        emu.reg_set(reg_a, imm16)
    elif modes == (MODES.REG, MODES.RELATIVE):
        # dest(reg_a) <- address of label
        emu.reg_set(reg_a, mask16(emu.pc.value + emu._signed16(imm16)))
    else:
        raise EmulatorException(f"unexpected MOV variant at 0x{emu.pc.value:04x}.")


def handle_push(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG,):
        emu._push_core(emu.reg_get(reg_a))
    elif modes == (MODES.IMM,):
        emu._push_core(imm16)
    else:
        raise EmulatorException(f"unexpected PUSH variant at 0x{emu.pc.value:04x}.")


def handle_pop(emu, decoded: tuple[int, ...]) -> None:
    _, reg_a, reg_b, _ = decoded
    # dest is in dddd slot (reg_b)
    emu.reg_set(reg_b, emu._pop_core())


def handle_add(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    # dest = reg_b (dddd), src = reg_a (ssss) or imm
    if modes == (MODES.REG, MODES.REG):
        result = emu._add_core(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        result = emu._add_core(emu.reg_get(reg_b), imm16)
    emu.reg_set(reg_b, result)


def handle_adc(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    carry = int(emu.flag_get(FLAG_C))
    if modes == (MODES.REG, MODES.REG):
        result = emu._add_core(emu.reg_get(reg_b), emu.reg_get(reg_a), carry)
    else:
        result = emu._add_core(emu.reg_get(reg_b), imm16, carry)
    emu.reg_set(reg_b, result)


def handle_sub(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu._sub_core(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        result = emu._sub_core(emu.reg_get(reg_b), imm16)
    emu.reg_set(reg_b, result)


def handle_sbc(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    borrow = int(emu.flag_get(FLAG_C))
    if modes == (MODES.REG, MODES.REG):
        result = emu._sub_core(emu.reg_get(reg_b), emu.reg_get(reg_a), borrow)
    else:
        result = emu._sub_core(emu.reg_get(reg_b), imm16, borrow)
    emu.reg_set(reg_b, result)


def handle_mul(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    dest = emu.reg_get(reg_b)
    src = emu.reg_get(reg_a) if modes == (MODES.REG, MODES.REG) else imm16
    full = dest * src
    result = mask16(full)
    carry = 1 if full > 0xFFFF else 0
    emu.set_all_flags(result == 0, carry, result & 0x8000 != 0, 0)
    emu.reg_set(reg_b, result)


def handle_mod(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    dest = emu.reg_get(reg_b)
    src = emu.reg_get(reg_a) if modes == (MODES.REG, MODES.REG) else imm16
    if src == 0:
        # division by zero, request hardware fault interrupt
        logger.warning(f"division by zero at 0x{emu.pc.value:04x}.")
        emu.raise_interrupt(0)
        return
    result = mask16(dest % src)
    emu.set_all_flags(result == 0, 0, result & 0x8000 != 0, 0)
    emu.reg_set(reg_b, result)


def handle_div(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    dest = emu.reg_get(reg_b)
    src = emu.reg_get(reg_a) if modes == (MODES.REG, MODES.REG) else imm16

    if src == 0:
        logger.warning(f"division by zero at 0x{emu.pc.value:04x}.")
        emu.raise_interrupt(0)
        return

    result = mask16(dest // src)
    remainder = dest % src

    emu.set_all_flags(result == 0, remainder != 0, result & 0x8000 != 0, 0)
    emu.reg_set(reg_b, result)


def handle_inc(emu, decoded: tuple[int, ...]) -> None:
    _, reg_a, reg_b, _ = decoded
    # dest is in dddd slot (reg_b)
    result = emu._add_core(emu.reg_get(reg_b), 1)
    emu.reg_set(reg_b, result)


def handle_dec(emu, decoded: tuple[int, ...]) -> None:
    _, reg_a, reg_b, _ = decoded
    # dest is in dddd slot (reg_b)
    result = emu._sub_core(emu.reg_get(reg_b), 1)
    emu.reg_set(reg_b, result)


def handle_lsh(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu._lsh_core(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        result = emu._lsh_core(emu.reg_get(reg_b), imm16)
    emu.reg_set(reg_b, result)


def handle_rsh(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu._rsh_core(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        result = emu._rsh_core(emu.reg_get(reg_b), imm16)
    emu.reg_set(reg_b, result)


def handle_asr(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu._asr_core(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        result = emu._asr_core(emu.reg_get(reg_b), imm16)
    emu.reg_set(reg_b, result)


def handle_and(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu.reg_get(reg_b) & emu.reg_get(reg_a)
    else:
        result = emu.reg_get(reg_b) & imm16
    emu.reg_set(reg_b, result)
    emu.flag_set(FLAG_Z, result == 0)


def handle_or(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu.reg_get(reg_b) | emu.reg_get(reg_a)
    else:
        result = emu.reg_get(reg_b) | imm16
    emu.reg_set(reg_b, result)
    emu.flag_set(FLAG_Z, result == 0)


def handle_not(emu, decoded: tuple[int, ...]) -> None:
    _, reg_a, reg_b, _ = decoded
    # dest is in dddd slot (reg_b)
    result = mask16(~emu.reg_get(reg_b))
    emu.reg_set(reg_b, result)
    emu.flag_set(FLAG_Z, result == 0)


def handle_xor(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG, MODES.REG):
        result = emu.reg_get(reg_b) ^ emu.reg_get(reg_a)
    else:
        result = emu.reg_get(reg_b) ^ imm16
    emu.reg_set(reg_b, result)
    emu.flag_set(FLAG_Z, result == 0)


def handle_swp(emu, decoded: tuple[int, ...]) -> None:
    _, reg_a, reg_b, _ = decoded
    # reg_a = ssss = op0, reg_b = dddd = op1
    a, b = emu.reg_get(reg_a), emu.reg_get(reg_b)
    emu.reg_set(reg_a, b)
    emu.reg_set(reg_b, a)


def handle_inb(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    # dest = reg_b (dddd), port = reg_a (ssss) or imm
    if modes == (MODES.REG, MODES.REG):
        result = emu.port_get(emu.reg_get(reg_a))
    else:
        result = emu.port_get(imm16)
    emu.reg_set(reg_b, result)
    emu.flag_set(FLAG_Z, result == 0)


def handle_outb(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    # src = reg_a (ssss), port = reg_b (dddd) or imm
    if modes == (MODES.REG, MODES.REG):
        emu.port_set(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        # OUTB imm, reg: port = imm, src = reg_a
        emu.port_set(imm16, emu.reg_get(reg_a))


def handle_cmp(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    # spec: flags <- dest - src
    # reg+reg: src=reg_a(ssss), dest=reg_b(dddd)
    # reg+imm: src=imm,  dest=reg_a(ssss) [dest in ssss anomaly]
    if modes == (MODES.REG, MODES.REG):
        emu._sub_core(emu.reg_get(reg_b), emu.reg_get(reg_a))
    else:
        emu._sub_core(emu.reg_get(reg_a), imm16)


def handle_jmp(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    if modes == (MODES.REG,):
        emu.pc.set(emu.reg_get(reg_a))
    elif modes == (MODES.IMM,):
        emu.pc.set(imm16)
    elif modes == (MODES.RELATIVE,):
        emu.pc.set(_jump_target(emu, imm16))
    elif modes == (MODES.OFF_POINTER,):
        base = _jump_target(emu, imm16)
        emu.pc.set(emu.read16(mask16(base + emu.reg_get(reg_a))))
    else:
        raise EmulatorException(f"unexpected JMP variant at 0x{emu.pc.value:04x}.")


def handle_jz(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_Z), decoded)


def handle_jnz(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, not emu.flag_get(FLAG_Z), decoded)


def handle_jc(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_C), decoded)


def handle_jnc(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, not emu.flag_get(FLAG_C), decoded)


def handle_ja(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_C) and not emu.flag_get(FLAG_Z), decoded)


def handle_jae(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_C) or emu.flag_get(FLAG_Z), decoded)


def handle_jb(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, not emu.flag_get(FLAG_C), decoded)


def handle_jbe(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, not emu.flag_get(FLAG_C) or emu.flag_get(FLAG_Z), decoded)


def handle_jg(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, not emu.flag_get(FLAG_Z) and (emu.flag_get(FLAG_N) == emu.flag_get(FLAG_O)), decoded)


def handle_jge(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_N) == emu.flag_get(FLAG_O), decoded)


def handle_jl(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_N) != emu.flag_get(FLAG_O), decoded)


def handle_jle(emu, decoded: tuple[int, ...]) -> None:
    _cond_jump(emu, emu.flag_get(FLAG_Z) or (emu.flag_get(FLAG_N) != emu.flag_get(FLAG_O)), decoded)


def handle_call(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    emu._push_core(emu.pc.value)
    if modes == (MODES.REG,):
        emu.pc.set(emu.reg_get(reg_a))
    elif modes == (MODES.IMM,):
        emu.pc.set(imm16)
    else:
        raise EmulatorException(f"unexpected CALL variant at 0x{emu.pc.value:04x}.")


def handle_ret(emu, _decoded: tuple[int, ...]) -> None:
    emu.pc.set(emu._pop_core())


def handle_int(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes

    if not emu.flag_get(FLAG_I):
        return

    vector = emu.reg_get(reg_a) if modes == (MODES.REG,) else imm16
    emu._execute_interrupt(vector)


def handle_iret(emu, _decoded: tuple[int, ...]) -> None:
    emu.f.set(emu._pop_core())
    emu.pc.set(emu._pop_core())


def handle_nop(_emu, _decoded: tuple[int, ...]) -> None:
    pass


def handle_blkcpy(emu, decoded: tuple[int, ...]) -> None:
    opcode, reg_a, reg_b, imm16 = decoded
    modes = OPCODE_FORMATS[opcode].modes
    dst = emu.reg_get(reg_b)   # dddd = dst address
    src = emu.reg_get(reg_a)   # ssss = src address
    count = imm16 if modes == (MODES.REG, MODES.REG, MODES.IMM) else emu.reg_get(2)  # C = index 2

    bank = emu._cached_bank
    if bank != 0 and 0xBC00 <= src <= 0xFDFF and 0xBC00 <= dst <= 0xFDFF:
        mem = emu._banked_memory
        s = (src - 0xBC00) * 2
        d = (dst - 0xBC00) * 2
    elif bank == 0:
        mem = emu.memory
        s = src * 2
        d = dst * 2
    else:
        # cross-boundary copy: fall back to word-by-word
        for i in range(count):
            emu.write16(dst + i, emu.read16(src + i))
        return

    n = count * 2
    mem[d:d + n] = mem[s:s + n]


handler_map: dict[INSTRUCTIONS, Callable[[Emulator, tuple[int, ...]], None]] = {
    INSTRUCTIONS.HALT : handle_halt,
    INSTRUCTIONS.GET  : handle_get,
    INSTRUCTIONS.PUT  : handle_put,
    INSTRUCTIONS.MOV  : handle_mov,
    INSTRUCTIONS.PUSH : handle_push,
    INSTRUCTIONS.POP  : handle_pop,
    INSTRUCTIONS.ADD  : handle_add,
    INSTRUCTIONS.ADC  : handle_adc,
    INSTRUCTIONS.SUB  : handle_sub,
    INSTRUCTIONS.SBC  : handle_sbc,
    INSTRUCTIONS.MUL  : handle_mul,
    INSTRUCTIONS.MOD  : handle_mod,
    INSTRUCTIONS.DIV  : handle_div,
    INSTRUCTIONS.INC  : handle_inc,
    INSTRUCTIONS.DEC  : handle_dec,
    INSTRUCTIONS.LSH  : handle_lsh,
    INSTRUCTIONS.RSH  : handle_rsh,
    INSTRUCTIONS.ASR  : handle_asr,
    INSTRUCTIONS.AND  : handle_and,
    INSTRUCTIONS.OR   : handle_or,
    INSTRUCTIONS.NOT  : handle_not,
    INSTRUCTIONS.XOR  : handle_xor,
    INSTRUCTIONS.SWP  : handle_swp,
    INSTRUCTIONS.INB  : handle_inb,
    INSTRUCTIONS.OUTB : handle_outb,
    INSTRUCTIONS.CMP  : handle_cmp,
    INSTRUCTIONS.JMP  : handle_jmp,
    INSTRUCTIONS.JZ   : handle_jz,
    INSTRUCTIONS.JNZ  : handle_jnz,
    INSTRUCTIONS.JC   : handle_jc,
    INSTRUCTIONS.JNC  : handle_jnc,
    INSTRUCTIONS.JA   : handle_ja,
    INSTRUCTIONS.JAE  : handle_jae,
    INSTRUCTIONS.JB   : handle_jb,
    INSTRUCTIONS.JBE  : handle_jbe,
    INSTRUCTIONS.JG   : handle_jg,
    INSTRUCTIONS.JGE  : handle_jge,
    INSTRUCTIONS.JL   : handle_jl,
    INSTRUCTIONS.JLE  : handle_jle,
    INSTRUCTIONS.CALL : handle_call,
    INSTRUCTIONS.RET  : handle_ret,
    INSTRUCTIONS.INT  : handle_int,
    INSTRUCTIONS.IRET  : handle_iret,
    INSTRUCTIONS.NOP   : handle_nop,
    INSTRUCTIONS.BLKCPY: handle_blkcpy,
}
