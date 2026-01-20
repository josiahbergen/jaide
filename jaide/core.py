# core.py
# core functions used by the emulator.
# josiah bergen, january 2026


def mask16(x: int) -> int: return x & 0xFFFF # mask to 16 bits

def _add_core(self, a: int, b: int, carry_in: int = 0) -> tuple[int, int, int]:
    full = a + b + carry_in
    result = mask8(full)
    carry = 1 if full > 0xFF else 0
    overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
    return result, carry, overflow

def _sub_core(self, a: int, b: int, borrow_in: int = 0) -> tuple[int, int, int]:
    full = a - b - borrow_in
    result = mask8(full)
    carry = 1 if a >= b + borrow_in else 0
    overflow = 1 if (((a ^ b) & 0x80) != 0 and ((a ^ result) & 0x80) != 0) else 0
    return result, carry, overflow

def _shl_core(self, a: int, b: int) -> tuple[int, int, int]:
    # TODO: test
    full = a << b
    result = mask8(full)
    carry = 1 if a & (1 << (8 - b)) else 0
    overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
    return result, carry, overflow

def _shr_core(self, a: int, b: int) -> tuple[int, int, int]:
    # TODO: test
    full = a >> b
    result = mask8(full)
    carry = 1 if a & (1 << (b - 1)) else 0
    overflow = 1 if (((a ^ b) & 0x80) == 0 and ((a ^ result) & 0x80) != 0) else 0
    return result, carry, overflow

def _push_core(self, value: int) -> None:
    self.sp = mask16(self.sp - 1) # decrement stack pointer
    self.write16(self.sp, value) # write value to new pointer location

def _pop_core(self) -> int:
    value = self.read16(mask16(self.sp)) # read value from stack
    self.sp = mask16(self.sp + 1) # increment stack pointer
    return value