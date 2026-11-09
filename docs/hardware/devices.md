
# devices

jaide supports a few devices:

| device                       | documentation                   |
| ---------------------------- | ------------------------------- |
| hard disk and filesystem     | [disk.md](devices/disk.md)         |
| graphics output              | [graphics.md](devices/graphics.md) |
| keyboard input               | [keyboard.md](devices/keyboard.md) |
| programmable interval timer  | [pit.md](devices/pit.md)           |
| real-time clock              | [rtc.md](devices/rtc.md)           |

## memory-mapped i/o

device registers live in the 256-word region from `0xFF00` to `0xFFFF`. access them with `GET` and `PUT`.

the keyboard, pit, and disk assert device interrupt lines `0x00`, `0x01`, and `0x02`, respectively. lines remain asserted until acknowledged via mmio. see the table below for more information.

| offset | device    | access | meaning                                  |
| ------ | --------- | ------ | ---------------------------------------- |
| `0x01` | keyboard  | R      | \* consume key, clear ready state        |
| `0x02` | keyboard  | R      | `1` when a key is ready, otherwise `0`   |
| `0x10` | pit       | R/W    | reload value                             |
| `0x11` | pit       | R/W    | \* flags: bit 0 enabled, bit 1 one-shot  |
| `0x20` | disk      | W      | command: `0` read, `1` write             |
| `0x21` | disk      | W      | sector number                            |
| `0x22` | disk      | W      | dma memory address                       |
| `0x23` | disk      | R      | \* status: `0` idle, `1` busy, `2` error |
| `0x30` | rtc       | R      | second                                   |
| `0x31` | rtc       | R      | minute                                   |
| `0x32` | rtc       | R      | hour                                     |
| `0x33` | rtc       | R      | day of year                              |
| `0x40` | display   | R/W    | bit 0 enables output                     |
| `0xFF` | system    | W      | system interface, see below              |

\* read lowers irq

unknown mmio reads return zero with a warning, and unknown writes have no defined result.
the emulator scans devices in registration order and is destructive when assigning addresses.

## system interface

the special mmio address `0xFFFF` controls the physical hardware.

| value  | command      | emulator behavior          | hardware behavior  |
| ------ | ------------ | -------------------------- | ------------------ |
| `0x00` | nop          | do nothing                 | do nothing         |
| `0x01` | reset        | clear ram/regs, set pc = 0 | pull reset pin low |
| `0x02` | halt         | set halted = true          | stop the clock     |
| `0x03` | shutdown     | shut down emulator process | disconnect power   |
| other  | _undefined_  | _undefined_                | _undefined_        |
