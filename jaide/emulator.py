# jaide.py
# jaide emulator
# josiah bergen, january 2026

from colorama import Fore as f
import os
from typing import Callable

from .util.logger import logger
from .constants import MNEMONICS, ADDRESSING_MODE_TO_SIZE, ADDRESSING_MODE_TO_STRING


MEMORY_SIZE = 0xFFFF + 1
REGISTERS = ["A", "B", "C", "D", "X", "Y"]

FLAG_C = 0 # carry
FLAG_Z = 1 # zero
FLAG_N = 2 # negative
FLAG_O = 3 # overflow

STS_HALT = 1 << 1
STS_POWER = 1

# opcodes
OP_LOAD = 0x0
OP_STORE = 0x1
OP_MOVE = 0x2
OP_PUSH = 0x3
OP_POP = 0x4
OP_ADD = 0x5
OP_ADDC = 0x6
OP_SUB = 0x7
OP_SUBB = 0x8
OP_INC = 0x9
OP_DEC = 0xA
OP_SHL = 0xB
OP_SHR = 0xC
OP_AND = 0xD
OP_OR = 0xE
OP_NOR = 0xF
OP_NOT = 0x10
OP_XOR = 0x11
OP_INB = 0x12
OP_OUTB = 0x13
OP_CMP = 0x14
OP_SEC = 0x15
OP_CLC = 0x16
OP_CLZ = 0x17
OP_JUMP = 0x18
OP_JZ = 0x19
OP_JNZ = 0x1A
OP_JC = 0x1B
OP_JNC = 0x1C
OP_INT = 0x1D
OP_HALT = 0x1E
OP_NOP = 0x1F

# addressing modes
MODE_NO_OPERANDS = 0b000
MODE_REG = 0b001
MODE_IMM8 = 0b010 
MODE_REG_REG = 0b011 
MODE_REG_IMM8 = 0b100 
MODE_REG_IMM16 = 0b101 
MODE_REG_REGPAIR = 0b110
MODE_IMM16 = 0b111


def mask8(x: int) -> int: return x & 0xFF # mask to 8 bits
def mask16(x: int) -> int: return x & 0xFFFF # mask to 16 bits


class EmulatorException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class Emulator:

    def __init__(self):

        # registers
        self.reg: dict[str, int] = {reg: 0 for reg in REGISTERS}

        self.pc: int = 0 # program counter
        self.sp: int = 0xFEFF # stack pointer
        self.f: int = 0 # flags
        
        self.mb: int = 0 # memory bank
        self.st: int = STS_POWER # status
        self.z: int = 0 # zero

        # memory and i/o
        self.memory: bytearray = bytearray(MEMORY_SIZE)
        self.ports: list[int] = [0] * 256 # 256 8-bit ports

        # debugger etc.
        self.breakpoints: set[int] = set[int]()
        self.halted: bool = False

        self.handlers: dict[int, Callable[[tuple[int, ...]]]] = {}
        self._populate_handlers()


    def _populate_handlers(self) -> None:
        self.handlers[OP_LOAD] = self.handle_load
        self.handlers[OP_STORE] = self.handle_store
        self.handlers[OP_MOVE] = self.handle_move
        self.handlers[OP_PUSH] = self.handle_push
        self.handlers[OP_POP] = self.handle_pop
        self.handlers[OP_ADD] = self.handle_add
        self.handlers[OP_ADDC] = self.handle_addc
        self.handlers[OP_SUB] = self.handle_sub
        self.handlers[OP_SUBB] = self.handle_subb
        self.handlers[OP_INC] = self.handle_inc
        self.handlers[OP_DEC] = self.handle_dec
        self.handlers[OP_SHL] = self.handle_shl
        self.handlers[OP_SHR] = self.handle_shr
        self.handlers[OP_AND] = self.handle_and
        self.handlers[OP_OR] = self.handle_or
        self.handlers[OP_NOR] = self.handle_nor
        self.handlers[OP_NOT] = self.handle_not
        self.handlers[OP_XOR] = self.handle_xor
        self.handlers[OP_INB] = self.handle_inb
        self.handlers[OP_OUTB] = self.handle_outb
        self.handlers[OP_CMP] = self.handle_cmp
        self.handlers[OP_SEC] = self.handle_sec
        self.handlers[OP_CLC] = self.handle_clc
        self.handlers[OP_CLZ] = self.handle_clz
        self.handlers[OP_JUMP] = self.handle_jump
        self.handlers[OP_JZ] = self.handle_jz
        self.handlers[OP_JNZ] = self.handle_jnz
        self.handlers[OP_JC] = self.handle_jc
        self.handlers[OP_JNC] = self.handle_jnc
        self.handlers[OP_INT] = self.handle_int
        self.handlers[OP_HALT] = self.handle_halt
        self.handlers[OP_NOP] = self.handle_nop


    # memory helpers
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
        print(f"loaded {len(binary)} bytes to memory at 0x{addr:04X}.")

    def read8(self, addr: int) -> int: 
        return self.memory[mask16(addr)]

    def write8(self, addr: int, value: int):
        self.memory[mask16(addr)] = mask8(value)
    
    def read16(self, addr: int) -> int: 
        return self.memory[mask16(addr)]

    def write16(self, addr: int, value: int):
        self.memory[mask16(addr)] = mask16(value)

    def disasm_at(self, addr: int) -> str:
        byte = self.memory[addr]
        opcode = byte >> 3
        addressing_mode = byte & 0b00000111
        all_bytes = self.memory[addr:addr+ADDRESSING_MODE_TO_SIZE[addressing_mode]]

        bytes_string = " ".join([f"{b:08b}" for b in all_bytes])
        return f"{bytes_string}: {MNEMONICS[opcode]} {ADDRESSING_MODE_TO_STRING[addressing_mode]}"

    # register helpers
    def reg_get(self, index: int) -> int:
        if index < 0 or index >= len(REGISTERS): return 0 # noqa: E701
        return mask8(self.reg[REGISTERS[index]])
    
    def reg_set(self, index: int, value: int) -> None:
        if index < 0 or index >= len(REGISTERS): return # noqa: E701
        self.reg[REGISTERS[index]] = mask8(value)

    # stack helpers
    # the stack grows downwards and sp always points to the element on the top of the stack
    def push_stack(self, value: int) -> None:
        self.sp = mask16(self.sp - 1) # decrement stack pointer
        self.write8(mask16(self.sp), value) # write value to new pointer location

    def pop_stack(self) -> int:
        value = self.read8(self.sp) # read value
        self.sp = mask16(self.sp + 1) # increment stack pointer
        return value

    # flag helpers
    def flag_get(self, bit: int) -> int:
        if bit < 0 or bit >= 4: return 0 # noqa: E701
        return (self.f >> bit) & 1

    def flag_set(self, bit: int, value: int) -> None:
        if bit < 0 or bit >= 4: return # noqa: E701
        # insane bit manipulation
        self.f = (self.f & ~(1 << bit)) | (value << bit)

    # port helpers
    def port_get(self, port: int) -> int:
        return mask8(self.ports[port])
    
    def port_set(self, port: int, value: int) -> None:
        self.ports[port] = mask8(value)

        # port 0 is special and will print the value to the console
        if port == 0:
            print(chr(value), end="", flush=True)


    # main fetch/decode
    def fetch(self) -> int:
        # fetch byte and increment program counter
        value = self.read8(self.pc)
        self.pc = mask16(self.pc + 1)
        return value

    def decode(self) -> tuple[int, ...]:
        first_byte = self.fetch()
        opcode = (first_byte >> 3) & 0b11111
        mode = first_byte & 0b111
        
        match mode:
            case 0b000: # no operands
                return (opcode, mode)
            
            case 0b001: # reg
                byte2 = self.fetch()
                reg_c = (byte2 >> 4) & 0x0F
                return (opcode, mode, reg_c)
            
            case 0b010: # imm8
                self.fetch()  # Skip unused byte
                imm8 = self.fetch()
                return (opcode, mode, imm8)
            
            case 0b011: # reg, reg
                byte2 = self.fetch()
                reg_d = (byte2 >> 4) & 0x0F
                reg_s = byte2 & 0x0F
                return (opcode, mode, reg_d, reg_s)
            
            case 0b100: # reg, imm8
                byte2 = self.fetch()
                reg_d = (byte2 >> 4) & 0x0F
                imm8 = self.fetch()
                return (opcode, mode, reg_d, imm8)
            
            case 0b101: # reg, imm16
                byte2 = self.fetch()
                reg_d = (byte2 >> 4) & 0x0F
                lo = self.fetch()
                hi = self.fetch()
                addr = (hi << 8) | lo
                return (opcode, mode, reg_d, addr)
            
            case 0b110: # reg, regpair
                byte2 = self.fetch()
                reg_d = (byte2 >> 4) & 0x0F
                reg_pair = self.fetch()
                return (opcode, mode, reg_d, reg_pair)
            
            case 0b111: # imm16
                self.fetch()  # Skip unused byte
                lo = self.fetch()
                hi = self.fetch()
                addr = (hi << 8) | lo
                return (opcode, mode, addr)
            case _:
                logger.error(f"invalid addressing mode {mode} at 0x{self.pc:04X}.")
                return (opcode, mode)

    # core arithmetic functions
    def _add_core(self, a:int, b:int) -> tuple[int, int, int]:
        res = a + b
        carry = 1 if res > 0xFF else 0
        # determine overflow
        overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ mask8(res)) & 0x80) != 0) else 0
        return mask8(res), carry, overflow

    def _sub_core(self, a:int, b:int) -> tuple[int, int, int]:
        res = mask8(a - b)
        carry = 1 if a - b < 0 else 0
        # yeah who knows what this does
        overflow = 1 if (((a ^ b) & 0x80) != 0 and ((a ^ res) & 0x80) != 0) else 0
        return res, carry, overflow

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
        return None

    # main run loop
    def repl(self):
        scope = "emulator.py:repl()"
        
        print("jaide emulator version 0.0.2")
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
            command_args = f"{command}{' ' if args else ''}{f.LIGHTBLACK_EX}{args}{f.RESET}"
            return f"{command_args:<30} {message}"

        while True:
            command, *args = input(f"{f.LIGHTBLACK_EX}jaide > {f.WHITE}").split()

            match command:
                case "run":
                    self.run()
                case "load":
                    if not assert_num_args(1, opt=1): continue # noqa: E701
                    file = args[0]
                    addr = parse_integer(1, base=16, default=0)
                    self.load_binary(file, addr)
                case "break":
                    if not assert_num_args(1, opt=0): continue # noqa: E701
                    addr = parse_integer(0, base=16)
                    self.breakpoints.add(addr)
                    print(f"set breakpoint at address 0x{addr:04X}.")
                case "blist":
                    num = len(self.breakpoints)
                    print(f"found {num} breakpoint{'' if num == 1 else 's'}{':' if num > 0 else '.'}")
                    for addr in self.breakpoints:
                        print(f"0x{addr:04X}: {self.disasm_at(addr)}")
                case "bclear":
                    num = len(self.breakpoints)
                    self.breakpoints.clear() # clear the set
                    print(f"removed {num} breakpoint{'' if num == 1 else 's'}.")
                case "step":
                    res = self.step()
                    if res: print(res) # noqa: E701
                case "regs":
                    line_1 = "    ".join([f"{reg}:  0x{self.reg_get(REGISTERS.index(reg)):02X}" for reg in REGISTERS])
                    line_2 = f"PC: 0x{self.pc:04X}  SP: 0x{self.sp:04X}  MB: 0x{self.mb:04X}  ST: 0x{self.st:02X}    Z:  0x{self.z:02X}"
                    print(line_1, line_2, sep="\n")
                case "mem":
                    if not assert_num_args(1, opt=1): continue # noqa: E701
                    if args[0] == "pc":
                        addr = self.pc
                    else:
                        addr = parse_integer(0, base=16)
                    length = parse_integer(1, default=16)
                    chunk = self.memory[addr:addr+length]
                    for i in range(0, len(chunk), 16):
                        row = chunk[i:i+16]
                        hex_bytes = " ".join(f"{b:02x}" for b in row)
                        print(f"0x{addr+i:04X} | {hex_bytes:<47}")
                case "disasm":
                    if not assert_num_args(0, opt=1): continue # noqa: E701
                    addr = parse_integer(0, base=16, default=self.pc)
                    print(self.disasm_at(addr))
                case "ports":
                    non_zero = [i for i in range(len(self.ports)) if self.ports[i] != 0]
                    if len(non_zero) == 0: print("no non-zero ports found.") # noqa: E701
                    for i in non_zero:
                        print(f"port {i}: 0x{self.ports[i]:02X}")
                case "clear":
                    os.system("cls" if os.name == "nt" else "clear")
                case "help":
                    print(help_string("load", "<path> [addr]", "load a binary file into memory"))
                    print(help_string("run", "", "execute until until a breakpoint or halt"))
                    print(help_string("break", "<addr>", "set a breakpoint at the given addrezss"))
                    print(help_string("blist", "", "list all breakpoints"))
                    print(help_string("bclear", "", "clear all breakpoints"))
                    print(help_string("step", "", "execute one instruction"))
                    print(help_string("regs", "", "display register values"))
                    print(help_string("mem", "<addr> <len>", "display memory contents"))
                    print(help_string("disasm", "[addr]", "disassemble instruction at address (or PC)"))
                    print(help_string("ports", "", "display non-zero port values"))
                    print(help_string("help", "", "show this message"))
                    print(help_string("clear", "", "clear the screen"))
                    print(help_string("quit", "", "exit the emulator"))
                case ":3":
                    print(":3")
                case "quit" | "exit":
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

    # operation handlers
    def handle_load(self, decoded: tuple[int, ...]) -> str | None: pass
    def handle_store(self, decoded: tuple[int, ...]) -> None: pass
    
    def handle_move(self, decoded: tuple[int, ...]) -> None:

        _, mode, *_ = decoded
        self.assert_addressing_mode(mode, [MODE_REG_IMM8, MODE_REG_REG])

        if mode == MODE_REG_IMM8:
            _, _, reg_d, imm8 = decoded
            self.reg_set(reg_d, imm8)
        else: # MODE_REG_REG:
            _, _, reg_s, reg_d = decoded # TODO: these might be swapped
            self.reg_set(reg_d, self.reg_get(reg_s))

    def handle_push(self, decoded: tuple[int, ...]) -> None: pass
    def handle_pop(self, decoded: tuple[int, ...]) -> None: pass
    def handle_add(self, decoded: tuple[int, ...]) -> None: pass
    def handle_addc(self, decoded: tuple[int, ...]) -> None: pass
    def handle_sub(self, decoded: tuple[int, ...]) -> None: pass
    def handle_subb(self, decoded: tuple[int, ...]) -> None: pass
    def handle_inc(self, decoded: tuple[int, ...]) -> None: pass
    def handle_dec(self, decoded: tuple[int, ...]) -> None: pass
    def handle_shl(self, decoded: tuple[int, ...]) -> None: pass
    def handle_shr(self, decoded: tuple[int, ...]) -> None: pass
    def handle_and(self, decoded: tuple[int, ...]) -> None: pass
    def handle_or(self, decoded: tuple[int, ...]) -> None: pass
    def handle_nor(self, decoded: tuple[int, ...]) -> None: pass
    def handle_not(self, decoded: tuple[int, ...]) -> None: pass
    def handle_xor(self, decoded: tuple[int, ...]) -> None: pass
    def handle_inb(self, decoded: tuple[int, ...]) -> None: pass
    
    def handle_outb(self, decoded: tuple[int, ...]) -> str | None:

        _, mode, *_ = decoded
        self.assert_addressing_mode(mode, [MODE_REG_IMM8, MODE_REG_REG])

        if mode == MODE_REG_IMM8:
            _, _, reg_s, imm8 = decoded
            port = imm8
        else: # MODE_REG_REG:
            _, _, reg_s, reg_d = decoded
            # the port is the value of the destination register
            port = self.reg_get(reg_d) 

        self.port_set(port, self.reg_get(reg_s))

    def handle_cmp(self, decoded: tuple[int, ...]) -> None: pass
    def handle_sec(self, decoded: tuple[int, ...]) -> None: pass
    def handle_clc(self, decoded: tuple[int, ...]) -> None: pass
    def handle_clz(self, decoded: tuple[int, ...]) -> None: pass
    def handle_jump(self, decoded: tuple[int, ...]) -> None: pass
    def handle_jz(self, decoded: tuple[int, ...]) -> None: pass
    def handle_jnz(self, decoded: tuple[int, ...]) -> None: pass
    def handle_jc(self, decoded: tuple[int, ...]) -> None: pass
    def handle_jnc(self, decoded: tuple[int, ...]) -> None: pass
    def handle_int(self, decoded: tuple[int, ...]) -> None: pass
    def handle_halt(self, decoded: tuple[int, ...]) -> None: self.halted = True
    def handle_nop(self, decoded: tuple[int, ...]) -> None: pass
