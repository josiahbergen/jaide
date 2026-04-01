# real time clock (rtc)

the real time clock is a simple read-only device that allows querying the current date and time.

## open ports

the rtc supports reading from four different ports:

| operation | port   | action             |
| --------- | ------ | ------------------ |
| read      | `0x30` | get current second |
| read      | `0x31` | get current minute |
| read      | `0x32` | get current hour   |
| read      | `0x33` | get day of year    |
