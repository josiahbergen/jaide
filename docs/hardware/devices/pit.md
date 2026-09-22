# programmable interrupt timer (pit)

the pit asserts interrupt line `0x05` at a defined, programmable interval.

## operation

the pit is disabled by default. it must be enabled by passing 0x01 to the flags (see below).

when on, the pit continuously counts down from its `reset` value. when the counter reaches zero, it asserts its interrupt line and resets the counter. reading the flags register acknowledges the event and deasserts the line.

## MMIO registers

the pit supports read/write communication on two registers:

| operation | address  | action          |
| --------- | -------- | --------------- |
| read      | `0xFE10` | get reset value |
| read      | `0xFE11` | get flags       |
| write     | `0xFE10` | set reset value |
| write     | `0xFE11` | set flags       |

## flags

there are two programmable flags:

| bit | flag     | definition                                             |
| --- | -------- | ------------------------------------------------------ |
| 0   | enabled  | enables/disables the device                            |
| 1   | one_shot | if true, counter will not reset after firing interrupt |
