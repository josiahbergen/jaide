# the jaide graphics controller

the jaide graphics controller is a graphical processing unit for the jaide computing system.

it uses memory bank `0x01` for vram, and contains 16Kib of font and attribute ROM.

## interrupts

the graphics controller has no irq line. reading its control register at `0xFF40` reports whether output is enabled and does not acknowledge an interrupt.

key input is delivered through the [keyboard controller](keyboard.md), which has its own irq line and acknowledgement register. reading the graphics control register does not acknowledge a keyboard event.

## resolution

the controller outputs 80x25 8x16 tiles, for a total size of 640×400.

## vram word structure

each glyph is defined by a 32-bit data structure:

| character | foreground color | background color | reserved | invert | blink |
| --------- | ---------------- | ---------------- | -------- | -----  | ----- |
| `0..15`   | `16..19`         | `20..23`         | `24..29` | `30`   | `31`  |

the attribute passed in a register is cell bits 16..31, one 16-bit word. write it as a binary immediate with bit 15 on the left. spaces below only separate the fields; the literal is those bits with the spaces removed.

```txt
b i ------ bbbb ffff
0 0 000000 0110 0001
```

`b` is blink, `i` is invert, and each `-` is reserved (write `0`). `bbbb` is the background color and `ffff` is the foreground color, both taken from the table below. the example is white (`0001`) on cyan (`0110`): `0b0000000001100001`.

note that this controller only reads from the first 4,000 words in vram (addresses 0x0000 -  0x0FA0 inclusive).

## colors

| color        | value | binary |
| ------------ | ----- | ------ |
| black        | `0`   | `0000` |
| white        | `1`   | `0001` |
| red          | `2`   | `0010` |
| green        | `3`   | `0011` |
| blue         | `4`   | `0100` |
| yellow       | `5`   | `0101` |
| cyan         | `6`   | `0110` |
| magenta      | `7`   | `0111` |
| gray         | `8`   | `1000` |
| light gray   | `9`   | `1001` |
| dark red     | `A`   | `1010` |
| dark green   | `B`   | `1011` |
| dark blue    | `C`   | `1100` |
| dark yellow  | `D`   | `1101` |
| dark cyan    | `E`   | `1110` |
| dark magenta | `F`   | `1111` |
