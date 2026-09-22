# filesystem

## disk controller

the disk controller allows for reading and writing to a hard disk.

### operation

the disk controller utilizes dma-style data transfer to and from a hard disk. on a read command, it copies 256 words into memory over 256 ticks (one word per tick). the device asserts interrupt line `0x06` on transfer complete. reading its completed status acknowledges the event and deasserts the line.

### mmio registers

the disk controller exposes four write registers and one read register:

| operation | address  | action         |
| --------- | -------- | -------------- |
| write     | `0xFE20` | command        |
| write     | `0xFE21` | sector number  |
| write     | `0xFE22` | memory address |
| read      | `0xFE23` | status         |

### commands

there are two supported commands:

| value  | command      | action                                   |
| ------ | ------------ | ---------------------------------------- |
| `0x00` | read sector  | copies data from a sector into memory    |
| `0x01` | write sector | writes data from memory to a disk sector |

### status flags

reading the status register returns a value from this table:

| value | flag  | meaning                           |
| ----- | ----- | --------------------------------- |
| 0     | idle  | device is idle                    |
| 1     | busy  | device is executing data transfer |
| 2     | error | device error                      |
