# the jaide graphics controller

the jaide graphics controller is a graphical processing unit for the jaide computing system.

it uses memory bank 1 for vram, and contains 16Kib of font and attribute ROM.

## resolution

the controller outputs 80x50 8x8 tiles, for a total size of 640×400.

## vram word structure

the controller exepects each word to consist of a certain structure:

| character | foreground color | background color | blink |
| --------- | ---------------- | ---------------- | ----- |
| 0..8      | 9..12            | 13..15           | 16    |

note that this controller only reads from the first 8,000 words in vram (addresses 0x0000 -  1F3F inclusive).
