# the jaide graphics controller

**_NOTE: the graphics controller is not implemented at this time._**

the jaide graphics controller is a graphical processing unit for the jaide computing system.

it uses memory bank 1 for vram, and contains 16Kib of font and attribute ROM.

## resolution

the controller outputs 80x25 8x16 tiles, for a total size of 640×400.

## vram word structure

the controller exepects each word to consist of a certain structure:

| character | foreground color | background color | blink |
| --------- | ---------------- | ---------------- | ----- |
| 0..8      | 9..12            | 13..15           | 16    |

in memory this is expressed little-endian, i.e.

note that this controller only reads from the first 8,000 words in vram (addresses 0x0000 -  1F3F inclusive).

## colors

| color        | value | background? |
| ------------ | ----- | ----------- |
| black        | 0     | yes         |
| white        | 1     | yes         |
| red          | 2     | yes         |
| green        | 3     | yes         |
| blue         | 4     | yes         |
| yellow       | 5     | yes         |
| cyan         | 6     | yes         |
| purple       | 7     | yes         |
| gray         | 8     | --          |
| light gray   | 9     | --          |
| dark red     | a     | --          |
| dark green   | b     | --          |
| dark blue    | c     | --          |
| dark yellow  | d     | --          |
| dark cyan    | e     | --          |
| dark magenta | f     | --          |
