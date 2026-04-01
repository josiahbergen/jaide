# programmable interrupt timer (pit)

the pit raises interrupt `0x05` at a defined, programmable interval.

## operation

the pit is disabled by default. it must be enabled by passing 0x01 to the flags (see below).

when on, the pit continuously counts down from its `reset` value, and when this counter reaches zero, it fires interrupt `0x05` and resets its counter.

## open ports

the pit supports read/write communication on two ports:

| operation | port   | action          |
| --------- | ------ | --------------- |
| read      | `0x10` | get reset value |
| read      | `0x11` | get flags       |
| write     | `0x10` | set reset value |
| write     | `0x11` | set flags       |

## flags

there are two programmable flags:

| bit | flag     | definition                                             |
| --- | -------- | ------------------------------------------------------ |
| 0   | enabled  | enables/disables the device                            |
| 1   | one_shot | if true, counter will not reset after firing interrupt |
