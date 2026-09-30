
# devices

jaide supports a few devices:

[disk](devices/disk.md): hard disk
[graphics](devices/graphics.md): graphics output
[keyboard](devices/keyboard.md): keyboard input
[pit](devices/pit.md): programmable interval timer
[rtc](devices/rtc.md): real-time clock

## memory-mapped i/o

device registers live in the 256-word region from `0xFE00` to `0xFEFF`. access them with `GET` and `PUT`.

device mmio is word-addressed and bank-independent. reads and writes are dispatched by the emulator's memory bus.

the keyboard, pit, and disk assert interrupt lines `0x04`, `0x05`, and `0x06`, respectively. lines remain asserted until acknowledged through mmio or cleared by reset. reading the keyboard key register, pit flags register, or disk status register acknowledges that device's event. reading keyboard readiness does not acknowledge a key. graphics and rtc have no interrupt lines.

see the table below for a listing of each device's registers.

| offset | device    | access | meaning                                             |
| ------ | --------- | ------ | --------------------------------------------------- |
| `0x01` | keyboard  | R      | consume key, clear ready state, and lower irq       |
| `0x02` | keyboard  | R      | `1` when a key is ready, otherwise `0`; irq unchanged |
| `0x10` | pit       | R/W    | reload value                                        |
| `0x11` | pit       | R/W    | flags: bit 0 enabled, bit 1 one-shot; read lowers irq |
| `0x20` | disk      | W      | command: `0` read, `1` write                        |
| `0x21` | disk      | W      | sector number                                       |
| `0x22` | disk      | W      | dma memory address                                  |
| `0x23` | disk      | R      | status: `0` idle, `1` busy, `2` error; read lowers irq |
| `0x30` | rtc       | R      | second                                              |
| `0x31` | rtc       | R      | minute                                              |
| `0x32` | rtc       | R      | hour                                                |
| `0x33` | rtc       | R      | day of year                                         |
| `0x40` | display   | R/W    | bit 0 enables output                                |
| `0xFF` | system    | W      | system interface, see below                         |

unknown mmio reads return zero with a warning, and unknown writes have no defined result.
the emulator scans devices in registration order and is destructive when assigning addresses.

## system interface

mmio address `0xFEFF` controls the physical hardware.

| value  | command      | emulator behavior          | hardware behavior  |
| ------ | ------------ | -------------------------- | ------------------ |
| `0x00` | nop          | do nothing                 | do nothing         |
| `0x01` | reset        | clear ram/regs, set pc = 0 | pull reset pin low |
| `0x02` | halt         | set halted = true          | stop the clock     |
| `0x03` | shutdown     | shut down emulator process | disconnect power   |
| other  | _undefined_  | _undefined_                | _undefined_        |
