# privilege and kernel entry

this document defines the smallest protected execution model needed to run one
foreground user program from the kernel shell.

## protected cpu state

the cpu has three internal values which normal instructions cannot access:

- `mode`: `supervisor` or `user`;
- `ssp`: the saved supervisor stack pointer; and
- `irq_allowed`: whether a device interrupt may be accepted.

reset sets supervisor mode, `sp = ssp = 0xfdff`, and `irq_allowed = 0`.

there is no programmable interrupt mask and there are no `sti` or `cli`
instructions. user code cannot read or write `irq_allowed`. kernel entry clears
it, `transfer` derives it from the target mode, and `wait` enables it only while
sleeping.

| transition                       | resulting `irq_allowed` |
| -------------------------------- | ----------------------- |
| reset                            | `0`                     |
| `transfer` to user               | `1`                     |
| `transfer` to supervisor         | `0`                     |
| syscall, fault, or interrupt entry | `0`                   |
| supervisor `wait`                | `1` while waiting       |

ordinary supervisor execution is therefore non-interruptible. user execution
may be interrupted between instructions, and supervisor code opens one atomic
interrupt window by executing `wait`.

## user protection

in user mode, instruction fetches and data accesses are limited to
`0x7000..0xafff` in the selected user bank. this includes stack accesses,
`call`, `ret`, and `bcp`.

user code cannot access kernel memory, vram, mmio, or another memory bank. it
cannot write `mb`. any prohibited operation raises a protection fault.

## context frame

all transfers between execution scopes use this seven-word frame:

| offset | field       |
| ------ | ----------- |
| `+0`   | target `pc` |
| `+1`   | target `sp` |
| `+2`   | flags       |
| `+3`   | `mb`        |
| `+4`   | mode        |
| `+5`   | event kind  |
| `+6`   | detail      |

event kind is `0` for a fault, `1` for a syscall, and `2` for a hardware
interrupt. detail is respectively the fault code, syscall number, or interrupt
number.

the frame does not contain general-purpose registers. a hardware-interrupt stub
must save and restore every register it uses. a syscall stub preserves registers
according to the syscall abi.

the frame also does not contain `irq_allowed`. it is not caller-controlled or
restored as data: kernel entry always clears it, and `transfer` derives its new
value from the validated target mode.

## kernel entry

all faults, syscalls, and hardware interrupts enter at the fixed kernel address
`0x0100`. the frame tells the kernel why it was entered; a vector table is not
required. the kernel places its common entry stub at that address and the boot
code jumps to a separate kernel startup label.

kernel entry is atomic. the cpu:

1. captures the current `pc`, `sp`, flags, `mb`, and mode;
2. enters supervisor mode and clears `irq_allowed`;
3. loads `sp` from `ssp` if the previous mode was user;
4. pushes a context frame on the supervisor stack; and
5. sets `pc = 0x0100`.

entry occurs only between completed instructions. a syscall saves the following
instruction, a hardware interrupt saves the next instruction to run, and a
fault saves the faulting instruction.

a fault raised in supervisor mode is fatal and halts the cpu. a fault raised in
user mode enters the kernel normally.

### syscall entry and interrupt entry

the two entries share the mode change, protected stack switch, context frame,
and fixed kernel entry address. they differ as follows:

| property | syscall | hardware interrupt |
| -------- | ------- | ------------------ |
| source | executing `syscall` in user mode | an asserted device line with `irq_allowed = 1` |
| timing | synchronous instruction | asynchronous, accepted between instructions |
| target `pc` | instruction after `syscall` | next instruction that would have run |
| event kind | `1` | `2` |
| detail | copy of register `a` | device interrupt number |
| previous mode | always user | user, or supervisor during `wait` |
| general registers | syscall abi permits results and clobbers | handler preserves all registers |
| acknowledgement | none | handler acknowledges the device through mmio |

## `syscall`

`syscall` is a zero-operand user-mode instruction. it enters the kernel with
event kind `1` and copies register `a` into the detail field. it cannot be
blocked or redirected by user code. using it in supervisor mode raises an
invalid-instruction fault; kernel code calls kernel functions directly.

the initial syscall abi is:

| registers  | contract                             |
| ---------- | ------------------------------------ |
| `a`        | syscall number, then primary result |
| `b`-`e`    | arguments or secondary results       |
| `x`-`z`    | preserved across a syscall           |
| `f`, `sp`, `mb` | restored by the protected transition |

user pointers include explicit lengths. the kernel rejects wrapping ranges and
ranges not completely inside `0x7000..0xafff` in the current user bank.

## `transfer`

`transfer` is a zero-operand supervisor instruction. it validates and consumes
the frame at `sp`, then transfers control into the scope described by it.

for a user target, `pc` and `sp` must be within `0x7000..0xafff`, `mb`
must select a user bank, and flags and mode must be valid. the cpu validates the
complete frame before changing state.

after consuming a frame for a user target, the cpu records the resulting kernel
`sp` in `ssp`. as one atomic operation, it restores `mb`, flags, `sp`, and `pc`,
sets `irq_allowed = 1`, and makes the target mode visible last.

a supervisor target restores an interrupted or saved kernel scope. the kernel
may construct a frame to start a user program or replace a syscall frame with a
supervisor frame to exit a program back to the shell. transfer to a supervisor
target sets `irq_allowed = 0`.

using `transfer` in user mode raises a protection fault.

## hardware interrupts

there is no `int` instruction. an emulated device exposes two values:

- a fixed interrupt number; and
- an asserted interrupt line.

each cpu step ticks every device, then samples their interrupt lines before
fetching an instruction. when `irq_allowed = 1`, the cpu accepts the asserted
line with the lowest interrupt number. ordinary supervisor execution has
`irq_allowed = 0`; `wait` is its only interruptible state.

acceptance performs kernel entry with event kind `2`. it does not clear the
device's line.

the handler reads or acknowledges the device through mmio, causing the device to
deassert its line, then restores its registers and uses `transfer`. interrupt
handlers must not execute `wait`.

## `wait`

`wait` is a zero-operand, supervisor-only instruction. it atomically completes,
sets `irq_allowed = 1`, and stops instruction fetch. devices continue to tick
while the cpu waits.

if an interrupt line is already asserted, the cpu accepts it immediately. if
not, the cpu remains waiting until a line is asserted. there is no interval in
which an interrupt can be handled after the kernel decides to wait but before
the cpu actually sleeps.

the accepted interrupt uses the instruction after `wait` as its target `pc`.
kernel entry immediately clears `irq_allowed`, ending the one-interrupt window.
after the handler acknowledges the device and executes `transfer`, supervisor
execution resumes after `wait` with `irq_allowed = 0` until another `wait`.

executing `wait` in user mode raises a protection fault. `halt` remains a
separate instruction which stops execution and does not create an interrupt
window.

initial interrupt numbers are:

| number | device   |
| ------ | -------- |
| `0x04` | keyboard |
| `0x05` | pit      |
| `0x06` | disk     |

## shell and blocking io

the shell is supervisor code and calls tty, filesystem, and device functions
directly. user programs use syscalls. only one foreground user program runs.

the shell may use `wait`; a keyboard interrupt reads the key into a kernel
queue and transfers back to the shell. interrupt handlers do not run shell code
or perform long operations.

the first blocking user syscalls sleep inside the kernel:

- keyboard input checks the kernel key queue and executes `wait` while it is
  empty;
- disk io validates the complete user buffer, captures its bank, starts the
  operation through mmio, and executes `wait` until completion is recorded;
- terminal output calls the kernel tty implementation directly.

a blocking input loop therefore has this shape:

```jasm
read_key__wait:
    call keyboard_queue_pop
    cmp a, no_key
    jnz read_key__done
    wait
    jmp read_key__wait
```

devices continue ticking while the cpu waits. the interrupt handler
acknowledges the device through mmio and records the key or completion in kernel
state. `transfer` returns to the instruction after `wait`, where the syscall
checks that state and either waits again or transfers back to user code.

when the shell launches a program, it loads one user bank, constructs a user
frame, and executes `transfer`. an exit syscall replaces its user return frame
with the saved supervisor shell context and executes `transfer`. the shell
then resets the terminal state and redraws its prompt.
