# real time clock (rtc)

the real time clock is a simple read-only device that allows querying the current date and time.

## MMIO registers

the rtc supports reading from four registers:

| operation | address  | action             |
| --------- | -------- | ------------------ |
| read      | `0xFE30` | get current second |
| read      | `0xFE31` | get current minute |
| read      | `0xFE32` | get current hour   |
| read      | `0xFE33` | get day of year    |
