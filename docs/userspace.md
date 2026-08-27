# userspace boundary

this document defines the processor boundary between the kernel and a user process.

## processor mode

jaide has two processor modes: `supervisor` and `user`.

the cpu has an internal register (`mde`) that controls the processor mode: zero and nonzero for `supervisor` and `user` respectively. the `mde` register cannot be modified by normal instructions.

### switching modes

the `mde` register is only modified in four specific circumstances:

- a cpu reset enters supervisor mode.
- a processor fault enters supervisor mode.
- `syscall` enters supervisor mode.
- `resume` restores the mode recorded in a saved context.

test

## memory and register access

supervisor mode may access the complete address space.

user mode may fetch, read, and write only within `0x7000..0xafff` in its selected memory bank. attempting to access _any_ other memory raises a protection fault.

all memory operations use the same checks, including instruction fetch, `push`, `pop`, `call`, `ret`, and `bcp`.

the user stack is located in the user bank and initially grows down from `0xafff`. the stack at `0xfdff` is kernel-only.

the `mb` register is considered supervisor-controlled, and cannot be modified while in `user` mode.

## supervisor stack

the cpu holds a protected supervisor stack pointer, `ssp`. it is internal processor state (like the mode register), and cannot be modified by normal instructions.

when execution enters the kernel from user mode, the cpu saves the user `sp`, loads `sp` from `ssp`, and creates a context frame on the supervisor stack. when execution returns to user mode, the cpu updates `ssp` and restores the saved user `sp`.

kernel code never runs on a user-controlled stack.

## `syscall`

`syscall` is a zero-operand instruction. userspace passes the syscall number and arguments in registers:


| register | use                            |
| -------- | ------------------------------ |
| `a`      | syscall number; primary result |
| `b`-`e`  | arguments; secondary results   |
| `x`-`z`  | scratch                        |


when executed in user mode, `syscall`:

1. records the address of the following instruction
2. captures the values of the `sp`, `mb`, and `f` registers
3. enters supervisor mode
4. switches to the supervisor stack (by copying `ssp` into `sp`)
5. creates a context frame (see below)
6. transfers execution to the kernel's syscall hander

userspace cannot supply a target address. executing `syscall` in supervisor mode raises an invalid-instruction fault; kernel code calls internal kernel functions directly.

## context frame

after kernel entry, `sp` points to this hardware-defined frame:


| offset | field         |
| ------ | ------------- |
| `+0`   | resume pc     |
| `+1`   | resume sp     |
| `+2`   | saved flags   |
| `+3`   | saved mb      |
| `+4`   | previous mode |
| `+5`   | event kind    |
| `+6`   | event detail  |


the event kind identifies a processor fault (`0`) or syscall (`1`), and the event detail contains the syscall number or fault code.

## `resume`

`resume` is a zero-operand, supervisor-only instruction. it validates and restores the context frame at the current supervisor `sp`.

before restoring user mode, the cpu verifies that:

- the destination `pc` and `sp` are within `0x7000`–`0xafff`
- `mb` selects a valid user bank
- the saved flags and mode contain valid values

the cpu validates the complete frame before changing any state. when returning to user mode, it updates `ssp`; it then restores `mb`, flags, `sp`, and `pc`, and restores the saved mode last.

the kernel may use `resume` to return from kernel entry or to launch a process from a context frame it has constructed. 

executing `resume` in user mode raises a protection fault.

## syscall entry

the protected word at `0xff80` contains the address of one kernel entry stub:

```jasm
syscall_entry:
    call syscall_dispatch
    resume
```

the dispatcher validates the syscall number and every user-provided argument. user pointers must include explicit lengths, must not wrap around, and must lie completely within the current user bank.

the public abi consists of the `syscall` instruction, syscall numbers, register conventions, data layouts, and error behavior. kernel function addresses and userspace library locations are not part of the abi.