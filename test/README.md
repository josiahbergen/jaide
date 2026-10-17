# Focused regression tests

Run from the project root with `uv run pytest` (or `.venv/bin/python -m pytest`).

Coverage is intentionally limited to four areas:

- Syscall/transfer: seven-word frame layout, saved return PC, stack switching,
  register preservation, context restoration, privilege checks, and atomic
  rejection of invalid frames.
- ALU/math: register and immediate operands, 16-bit wraparound, carry/borrow,
  signed overflow, division faults, comparisons, bitwise flag preservation,
  and shift edge cases.
- Memory protection: bank isolation, shared memory outside the bank window,
  user address boundaries, protected fetch/read/write, and MMIO side-effect
  prevention. Address boundaries and bank selection make this failure-prone.
- Control flow: assembled conditional branches, backward loops, signed relative
  offsets, address wraparound, and call/return stack balance. This checks the
  agreement between assembler encoding and emulator execution.

The tests use a real emulator with devices disabled. Instruction tests pass
through the real assembler and fetch/decode/execute path; invalid transition
tests call handlers directly so the CPU's supervisor double-fault interaction
does not obscure validation assertions.

Shift regressions cover both register and immediate operands. A zero count
preserves the value and clears carry. Counts greater than 16 produce zero and
clear carry. A count of exactly 16 produces zero with the last shifted-out bit
in carry. Right shift by zero and left shift by more than 16 previously crashed
while calculating carry; these cases now run as ordinary passing tests.
