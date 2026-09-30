# programmable interrupt timer (pit)

the pit asserts interrupt line `0x05` at a defined, programmable interval.

## operation

the pit is disabled by default. it must be enabled by passing 0x01 to the flags (see below).

when on, the pit continuously counts down from its `reset` value. when the counter reaches zero, it asserts its interrupt line and resets the counter.

## interrupt acknowledgement

reading the flags register at `0xFE11` returns the current enabled and one-shot flags and lowers irq line `0x05`. acknowledgement does not change the flags or counter. reading the reset value at `0xFE10` leaves the line unchanged.

writes to either register do not acknowledge an event. disabling the timer leaves an already asserted line pending until acknowledged or reset. a one-shot expiration also remains pending after the timer disables itself.

multiple expirations before acknowledgement coalesce into one pending interrupt; the device does not report how many expirations occurred. cpu acceptance does not lower the line. reset lowers the line and disables the timer.

## MMIO registers

the pit supports read/write communication on two registers:

| operation | address  | action                            |
| --------- | -------- | --------------------------------- |
| read      | `0xFE10` | get reset value; irq unchanged    |
| read      | `0xFE11` | get flags and acknowledge event   |
| write     | `0xFE10` | set reset value                   |
| write     | `0xFE11` | set flags                         |

## flags

there are two programmable flags:

| bit | flag     | definition                                             |
| --- | -------- | ------------------------------------------------------ |
| 0   | enabled  | enables/disables the device                            |
| 1   | one_shot | if true, counter will not reset after firing interrupt |
