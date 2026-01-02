from typing import Callable
from .emulator import emu

def generate_handlers() -> dict[int, Callable[[tuple[int, ...]], None]]:

    return {
        OP_LOAD:  handle_load,
        OP_STORE: handle_store,
        OP_MOVE:  handle_move,
        OP_PUSH:  handle_push,
        OP_POP:   handle_pop,
        OP_ADD:   handle_add,
        OP_ADDC:  handle_addc,
        OP_SUB:   handle_sub,
        OP_SUBB:  handle_subb,
        OP_INC:   handle_inc,
        OP_DEC:   handle_dec,
        OP_SHL:   handle_shl,
        OP_SHR:   handle_shr,
        OP_AND:   handle_and,
        OP_OR:    handle_or,
        OP_NOR:   handle_nor,
        OP_NOT:   handle_not,
        OP_XOR:   handle_xor,
        OP_INB:   handle_inb,
        OP_OUTB:  handle_outb,
        OP_CMP:   handle_cmp,
        OP_SEC:   handle_sec,
        OP_CLC:   handle_clc,
        OP_CLZ:   handle_clz,
        OP_JUMP:  handle_jump,
        OP_JZ:    handle_jz,
        OP_JNZ:   handle_jnz,
        OP_JC:    handle_jc,
        OP_JNC:   handle_jnc,
        OP_INT:   handle_int,
        OP_HALT:  handle_halt,
        OP_NOP:   handle_nop
    }

def handle_load(decoded: tuple[int, ...]) -> None: pass
def handle_store(decoded: tuple[int, ...]) -> None: pass
def handle_move(decoded: tuple[int, ...]) -> None: pass
def handle_push(decoded: tuple[int, ...]) -> None: pass
def handle_pop(decoded: tuple[int, ...]) -> None: pass
def handle_add(decoded: tuple[int, ...]) -> None: pass
def handle_addc(decoded: tuple[int, ...]) -> None: pass
def handle_sub(decoded: tuple[int, ...]) -> None: pass
def handle_subb(decoded: tuple[int, ...]) -> None: pass
def handle_inc(decoded: tuple[int, ...]) -> None: pass
def handle_dec(decoded: tuple[int, ...]) -> None: pass
def handle_shl(decoded: tuple[int, ...]) -> None: pass
def handle_shr(decoded: tuple[int, ...]) -> None: pass
def handle_and(decoded: tuple[int, ...]) -> None: pass
def handle_or(decoded: tuple[int, ...]) -> None: pass
def handle_nor(decoded: tuple[int, ...]) -> None: pass
def handle_not(decoded: tuple[int, ...]) -> None: pass
def handle_xor(decoded: tuple[int, ...]) -> None: pass
def handle_inb(decoded: tuple[int, ...]) -> None: pass
def handle_outb(decoded: tuple[int, ...]) -> None: pass
def handle_cmp(decoded: tuple[int, ...]) -> None: pass
def handle_sec(decoded: tuple[int, ...]) -> None: pass
def handle_clc(decoded: tuple[int, ...]) -> None: pass
def handle_clz(decoded: tuple[int, ...]) -> None: pass
def handle_jump(decoded: tuple[int, ...]) -> None: pass
def handle_jz(decoded: tuple[int, ...]) -> None: pass
def handle_jnz(decoded: tuple[int, ...]) -> None: pass
def handle_jc(decoded: tuple[int, ...]) -> None: pass
def handle_jnc(decoded: tuple[int, ...]) -> None: pass
def handle_int(decoded: tuple[int, ...]) -> None: pass
def handle_halt(decoded: tuple[int, ...]) -> None: halted = True
def handle_nop(decoded: tuple[int, ...]) -> None: pass
