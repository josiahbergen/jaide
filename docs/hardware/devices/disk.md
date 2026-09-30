# filesystem

## disk controller

the disk controller allows for reading and writing to a hard disk.

### operation

the disk controller utilizes dma-style data transfer to and from a hard disk. each read or write command copies 256 words over 256 ticks (one word per tick), using the memory bank selected when the command starts. the device asserts interrupt line `0x06` on transfer complete, after persisting writes to the disk image. an invalid command or out-of-range sector also asserts the line with error status.

### interrupt acknowledgement

reading the status register at `0xFE23` returns the current status and lowers irq line `0x06`. the read does not change the status or cancel an active transfer. this acknowledgement applies to every status read, including polling reads while busy. the eventual completion of an active transfer asserts the line again.

successful reads and writes both report idle status on completion; failures report error status. software must track which command it issued and record the returned status before starting another command.

writes to the command, sector, and memory-address registers do not acknowledge an event. cpu acceptance does not lower the line. reset lowers the line, cancels an active transfer, and restores idle status.

### mmio registers

the disk controller exposes three write registers and one read register:

| operation | address  | action                           |
| --------- | -------- | -------------------------------- |
| write     | `0xFE20` | command                          |
| write     | `0xFE21` | sector number                    |
| write     | `0xFE22` | memory address                   |
| read      | `0xFE23` | get status and acknowledge event |

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
