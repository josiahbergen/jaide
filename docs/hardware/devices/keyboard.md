# keyboard controller

the keyboard controller receives translated key codes from the graphics controller and asserts interrupt line `0x04` when a key is ready.

## mmio registers

| operation | address  | action                                           |
| --------- | -------- | ------------------------------------------------ |
| read      | `0xFE01` | consume the pending key and acknowledge its event |
| read      | `0xFE02` | get ready state without acknowledging the event   |

## interrupt acknowledgement

reading `0xFE01` returns the pending key code, clears the ready state, and lowers the irq line in the same operation. if no key is ready, it returns zero.

reading `0xFE02` returns `1` when a key is ready and `0` otherwise. it leaves the pending key and irq line unchanged, so software can check readiness before consuming the key.

the pending key remains available until consumed. additional keys stay queued; after the pending key is read, the next device tick presents the next queued key and asserts the line again.

cpu acceptance of the interrupt does not lower the line. reset lowers the line and clears both the pending key and queued keys.
