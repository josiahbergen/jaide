# real time clock (rtc)

the real time clock is a simple read-only device that allows querying the current date and time.

## interrupts

the rtc has no irq line. reads from `0xFF30` through `0xFF33` only return time values; they do not acknowledge an interrupt.

## MMIO registers

the rtc supports reading from four registers:

| operation | address  | action             |
| --------- | -------- | ------------------ |
| read      | `0xFF30` | get current second |
| read      | `0xFF31` | get current minute |
| read      | `0xFF32` | get current hour   |
| read      | `0xFF33` | get day of year    |
