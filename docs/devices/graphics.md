# the jaide graphics controller

the jaide graphics controller is a graphical processing unit for the jaide computing system.

it uses memory bank `0x01` for vram, and contains 16Kib of font and attribute ROM.

## resolution

the controller outputs 80x25 8x16 tiles, for a total size of 640×400.

## vram word structure

each glyph is defined by a 32-bit data structure:

| character | foreground color | background color | reserved | invert | blink |
| --------- | ---------------- | ---------------- | -------- | -----  | ----- |
| `0..15`   | `16..19`         | `20..23`         | `24..29` | `30`   | `31`  |

in raw memory each word expressed in little-endian form, but the words themselves remain in order.

```txt
lo       hi       ------ib fore back 
xxxxxxxx xxxxxxxx xxxxxxxx xxxx xxxx
```

note that this controller only reads from the first 4,000 words in vram (addresses 0x0000 -  0x0FA0 inclusive).

## colors

| color        | value |
| ------------ | ----- |
| black        | `0`   |
| white        | `1`   |
| red          | `2`   |
| green        | `3`   |
| blue         | `4`   |
| yellow       | `5`   |
| cyan         | `6`   |
| purple       | `7`   |
| gray         | `8`   |
| light gray   | `9`   |
| dark red     | `A`   |
| dark green   | `B`   |
| dark blue    | `C`   |
| dark yellow  | `D`   |
| dark cyan    | `E`   |
| dark magenta | `F`   |
