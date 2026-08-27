# userspace roadmap

this roadmap defines the boundary between the jaide kernel and user programs. its first two application milestones are a `cat`-style program and a character-graphics demo.

the processor-mode and kernel-entry contract is defined in [userspace-boundary.md](userspace-boundary.md).

## goals

- run an untrusted program without giving it direct access to the kernel, other process banks, vram, or mmio.
- expose a small syscall abi that does not depend on kernel function addresses.
- keep terminal behavior, positioned character graphics, formatting, and filesystem access as separate layers.
- statically link ordinary userspace libraries at any location within a program image.
- prove the design with `cat` first and a graphics demo second.

multitasking, dynamic linking, virtual terminals, and a general-purpose executable format are not required for these milestones.

## privilege contract

the cpu has an internal execution mode with two values: `supervisor` and `user`. this state is not part of the writable flags register.

ordinary instructions cannot modify the mode directly. only cpu control logic may change it as part of an atomic transition:

- reset starts in supervisor mode.
- the selected syscall-entry mechanism changes user mode to supervisor mode while saving the user context and switching to a protected kernel stack.
- a processor fault or hardware interrupt enters supervisor mode through the same protected context-save path.
- a supervisor-only resume operation restores a complete user context and changes to user mode. the kernel uses this operation for both initial process entry and return from a syscall or fault.

user processes enter the kernel with the zero-operand `syscall` instruction and return through the supervisor-only `resume` instruction. kernel function addresses are never an abi.

## memory access

in supervisor mode, the kernel may access the complete address space and the currently selected memory bank.

in user mode, instruction fetches, reads, writes, and stack accesses are limited to `0x7000`–`0xafff` in the process's selected bank. all other accesses raise a protection fault. in particular, user mode cannot directly access:

- kernel code or data;
- vram;
- mmio;
- the interrupt vector table;
- the kernel stack; or
- another process's bank.

`mb` is supervisor-controlled while a user process is running. the initial userspace stack grows downward from `0xafff`; the stack at `0xfdff` is reserved for the kernel.

the syscall and fault entry path must switch stacks before executing ordinary kernel code. the kernel must never trust a user-supplied stack pointer as its own stack.

device dma must obey the same isolation boundary. a driver may target a user bank only after the kernel validates the complete destination or source range and captures the intended bank.

## syscall boundary

the public syscall abi consists only of:

- the protected entry mechanism;
- syscall numbers;
- argument and result registers;
- user-memory data layouts; and
- documented error behavior.

userspace may invoke any public syscall without using a library wrapper. wrappers provide names and calling convenience, not authority. every handler therefore validates its syscall number, scalar arguments, pointers, lengths, coordinates, handles, and permissions.

pointer-plus-length interfaces are preferred over null-terminated kernel reads. range validation must reject wraparound and ensure the entire range lies within `0x7000`–`0xafff` in the current process bank.

shutdown, reset, raw device control, and direct vram access are not public user operations. public syscalls that affect global state must be deliberately authorized rather than hidden behind a library.

## process contract

the first process format is a flat, statically linked image loaded at `0x7000` in one memory bank. before implementing the loader, define:

- the initial pc and sp;
- which registers contain `argc` and `argv`, or the address of a startup block;
- the in-memory argument-string layout;
- which registers are preserved across a syscall;
- the exit-code convention;
- executable size validation; and
- how the kernel distinguishes the foreground process from the shell.

the loader owns bank selection, rejects images that collide with the initial stack, constructs the startup state, and enters user mode through the supervisor-only resume operation. process exit restores the kernel context and resets the complete console state before redrawing the shell.

## kernel and userspace layers

```text
         userspace application
  libfmt / libtui / filesystem helpers
                  |
         libsys syscall wrappers
                  |
        protected syscall boundary
                  |
        kernel syscall adapters
                  |
     tty       display     filesystem
       \          |          /
       kernel/device primitives
```

kernel code calls kernel primitives directly. it does not invoke its own syscall boundary or call code from a user library. a formatting engine may share source between kernel and userspace builds, but `kprintf` emits through the internal tty interface while userspace `printf` emits through public console syscalls.

## terminal and character graphics

the display layer owns the vram layout and provides cursor-independent cell operations. each positioned operation supplies the complete glyph and attribute and does not alter terminal state.

initial display operations:

- put one complete cell at `(x, y)`;
- copy a bounded run of complete cells; and
- fill or clear a bounded region.

the tty layer is built on the display layer and owns cursor position, current terminal attributes, newline handling, wrapping, and scrolling.

initial terminal operations:

- write a buffer with an explicit length;
- write one character;
- clear and reset the terminal;
- get or set the cursor; and
- set the terminal attribute.

the foreground process has exclusive use of the physical console. positioned drawing does not change the tty cursor. process launch and exit have explicit console-reset behavior so attributes and cursor state cannot leak between the shell and an application.

userspace `libfmt` builds `puts`, integer conversion, and `printf`-style formatting on terminal writes. userspace `libtui` builds positioned text, lines, boxes, and region fills on display syscalls. neither library knows the physical vram address.

## filesystem api

the first userspace filesystem api needs only:

- open a path for reading;
- read into a bounded user buffer;
- close a handle; and
- distinguish eof from an error.

before exposing it, settle whether file sizes, offsets, and read lengths are bytes or 16-bit words. the disk format, kernel api, tools, and documentation must use one convention. path encoding, maximum path length, invalid-handle behavior, and partial reads must also be explicit.

the kernel validates user buffers before starting a read and records the current process bank for any asynchronous or dma-backed transfer. userspace wrappers may make the register abi pleasant, but the kernel remains correct when a program invokes the raw syscall.

## implementation sequence

### 1. freeze the boundary

- keep the `syscall` and `resume` contract synchronized across the cpu, emulator, kernel, assembler, and documentation.
- specify the saved user context and kernel stack transition.
- finalize the user memory permissions and privileged registers.
- finalize syscall register preservation, pointer validation, and error codes.
- choose byte or word units for files and buffers.

done when the cpu, emulator, kernel, assembler, and application abi can be implemented without guessing about a transition or data layout.

### 2. implement privilege enforcement in the emulator

- add the internal mode state and supervisor reset state.
- enforce user fetch, read, write, stack, `mb`, vram, and mmio restrictions.
- implement protected syscall entry, protected user resume, kernel stack switching, and protection faults.
- add tests for direct kernel jumps, invalid pointers, cross-bank access, vram writes, mmio access, and malformed returns.

done when deliberately hostile test programs remain contained in their own banks and valid syscalls return safely.

### 3. load and exit a process

- load one checked flat image into a selected bank.
- construct its startup context and bank-local stack.
- enter it in user mode.
- implement process exit and restoration of the kernel shell.

small machine-code fixtures may be used to test entry and exit, but they are not product applications.

done when a process can start, invoke one harmless syscall, exit with a status, and leave the shell and kernel stack intact.

### 4. make the syscall boundary safe

- centralize user-range and overflow validation.
- implement safe copy-to-user and copy-from-user helpers.
- replace unbounded string reads with explicit lengths.
- audit filesystem dma and remove privileged system controls from the user syscall table.
- give all syscall failures stable error results.

done when malformed syscall arguments cannot read or overwrite supervisor memory or another bank.

### 5. build the first real program: `cat`

- finalize read-only `open`, `read`, and `close` syscalls.
- provide `libsys` wrappers and the process argument convention.
- expose bounded terminal writes.
- implement `cat` as a read/write loop using a fixed-size buffer and partial-read handling.

`cat` must accept a path argument, stream files larger than its buffer, distinguish eof from an error, report failures through terminal output, close its handle, and return a useful exit code.

done when a user process can print an arbitrary text file without direct disk, kernel-memory, or vram access.

### 6. separate display and tty internals

- move raw cell addressing and writes into a display module.
- build tty cursor, wrapping, scrolling, and attributes on that module.
- expose bounded positioned-cell syscalls with explicit attributes.
- add bulk cell-copy or region-fill only after the one-cell path works end to end.
- add `libfmt` and `libtui` above `libsys`.

done when terminal output and positioned drawing share the display implementation without sharing cursor policy.

### 7. build the graphics demo

- draw characters at stable coordinates with explicit foreground, background, invert, and blink attributes.
- exercise positioned text, lines or boxes, region clearing, and repeated updates.
- use the public keyboard api to interact or exit.
- return to a freshly reset shell console.

done when the demo produces a character-graphics screen without direct vram access and exits without leaving display state behind.

### 8. reproduce the settled cpu contract in hardware

implement the already-tested privilege, protected-transition, stack-switching, and memory-gating behavior in the circuit. use the emulator tests as architectural conformance cases rather than designing different semantics in hardware.

## deferred work

- multiple runnable or background processes;
- scheduling and preemption;
- virtual terminals and per-process console state;
- dynamic libraries or fixed-address userspace trampolines;
- writable files beyond what the first applications require;
- pixel graphics; and
- a versioned executable-file format.
