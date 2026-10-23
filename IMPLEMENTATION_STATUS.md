# Implementation status

_Updated October 10, 2026._

## Remaining work

### TODO

- perserve registers during all hardware entries

### 1. Finish emulator correctness

- Fix the assembler's absolute-jump check so `--nolink` permits the boot image.
- Match the documented event numbers: fault `0`, syscall `1`, IRQ `2`.
- Catch faults from fetch and decode as well as instruction execution.
- Make supervisor faults stop the CPU cleanly rather than entering another frame
  or interactively resetting.
- Add architectural tests for protection, frames, transfers, `wait`, faults, and
  device IRQ acknowledgement. There is currently no test suite.

### 2. Connect the kernel to the new boundary

- Put a common entry stub at `0x0100`; boot must jump to a separate startup label.
- Dispatch the frame's event kind and detail to syscall, fault, or IRQ handling.
- Preserve registers in IRQ handlers, acknowledge the device, then `transfer`.
- Route user `syscall` instructions into the existing internal syscall table.
- Remove the temporary startup `break` and `halt` once normal boot resumes.

### 3. Prove one complete user-process lifecycle

- Load a checked flat program into one user bank.
- Construct its initial frame and `transfer` into user mode.
- Execute one harmless syscall and return to user mode.
- Implement `exit` by restoring the saved shell context.

This is the next important milestone: a tiny program should start, call the
kernel, exit, and leave the shell and kernel stack intact.

### 4. Add safe blocking I/O

- Maintain a kernel keyboard queue populated by the keyboard IRQ handler.
- Use `wait` inside blocking keyboard and disk syscalls.
- Validate user buffer ranges and capture the user's bank before disk DMA.
- Add bounded copy-to-user and copy-from-user helpers and stable error results.

### 5. Build real user programs

Start with a small `cat`-style program to prove file input and terminal output.
Then add the text editor using the same public file, terminal, and keyboard
syscalls. Hardware implementation should follow only after these semantics are
covered by emulator conformance tests.

## Recommended next task

Implement and test the `0x0100` common kernel entry stub. Until that exists,
syscalls and hardware IRQs can enter supervisor mode but cannot be handled by the
kernel correctly.
