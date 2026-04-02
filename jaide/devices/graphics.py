# graphics.py
# graphics controller device for the jaide emulator.
# josiah bergen, april 2026

import time
from collections import deque
from pathlib import Path
from typing import Callable

import pygame

from ..util.logger import logger
from .device import Device

GRAPHICS_COLS   = 80
GRAPHICS_ROWS   = 25
GRAPHICS_CHAR_W = 8
GRAPHICS_CHAR_H = 16
GRAPHICS_WIDTH  = GRAPHICS_COLS * GRAPHICS_CHAR_W  # 640
GRAPHICS_HEIGHT = GRAPHICS_ROWS * GRAPHICS_CHAR_H  # 400
VRAM_CELLS      = GRAPHICS_COLS * GRAPHICS_ROWS    # 2000

FRAME_INTERVAL  = 1 / 30  # seconds between renders, smoooth 30fps

COLORS: list[tuple[int, int, int]] = [
    (0,   0,   0  ),  # 0:  black
    (255, 255, 255),  # 1:  white
    (255, 0,   0  ),  # 2:  red
    (0,   255, 0  ),  # 3:  green
    (0,   0,   255),  # 4:  blue
    (255, 255, 0  ),  # 5:  yellow
    (0,   255, 255),  # 6:  cyan
    (255, 0,   255),  # 7:  purple
    (128, 128, 128),  # 8:  gray
    (192, 192, 192),  # 9:  light gray
    (128, 0,   0  ),  # 10: dark red
    (0,   128, 0  ),  # 11: dark green
    (0,   0,   128),  # 12: dark blue
    (128, 128, 0  ),  # 13: dark yellow
    (0,   128, 128),  # 14: dark cyan
    (128, 0,   128),  # 15: dark magenta
]


class GraphicsDevice(Device):
    def __init__(self, irq: Callable[[int], None], key_queue: deque, vram: bytearray):
        """Graphics controller. Renders VRAM (bank 1) to a pygame window.

        vram      -- reference to emulator.banks[0] (VRAM bank)
        key_queue -- shared deque; key events are appended here for KeyboardDevice
        """
        super().__init__(irq)

        self.vram: bytearray     = vram
        self.enabled: bool       = True
        self.key_queue: deque    = key_queue
        self._last_render: float = 0.0  # seconds

        self._glyphs: list[bytes]   = _load_glyphs()
        self._framebuf: bytearray   = bytearray(GRAPHICS_WIDTH * GRAPHICS_HEIGHT * 3)
        self._blink_timer: int      = 0
        self._last_hash: int | None = None

        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode((GRAPHICS_WIDTH, GRAPHICS_HEIGHT))
        pygame.display.set_caption("jaide graphics controller output")

        self.write_dispatch[0x40] = self._set_control
        self.read_dispatch[0x40]  = lambda: 0x01 if self.enabled else 0x00

    def _set_control(self, value: int) -> None:
        self.enabled = bool(value & 0x01)

    def tick(self) -> None:

        now = time.monotonic()
        if now - self._last_render < FRAME_INTERVAL:
            # still within frame interval, do nothing
            return
        self._last_render = now

        # drain pygame events; push key events to shared queue for KeyboardDevice
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                # closed button pressed, ignore
                return

            if event.type == pygame.KEYDOWN:
                scancode = _translate_key(event)
                if scancode:
                    self.key_queue.append(scancode)

        # render pixels
        if self.enabled:
            self._render()
        else:
            self._render_inactive()

        pygame.display.flip() # draw

    def _render(self) -> None:

        self._blink_timer = (self._blink_timer + 1) % 8
        blink_on = self._blink_timer < 4

        if not self._glyphs:
            return

        # skip re-render if VRAM content and blink phase haven't changed
        vram_snapshot = bytes(self.vram[:VRAM_CELLS * 4])
        h = hash(vram_snapshot + bytes([blink_on]))
        if h == self._last_hash:
            return
        self._last_hash = h

        fb = self._framebuf
        for cell_idx in range(VRAM_CELLS):
            # each cell is two words (4 bytes), little-endian
            # 32-bit layout: char[0..15] | fg[16..19] | bg[20..23] | reserved[24..29] | invert[30] | blink[31]
            i    = cell_idx * 4
            cell = self.vram[i] | (self.vram[i+1] << 8) | (self.vram[i+2] << 16) | (self.vram[i+3] << 24)

            char_code = cell & 0xFFFF
            fg_idx    = (cell >> 16) & 0x0F
            bg_idx    = (cell >> 20) & 0x0F
            invert    = bool((cell >> 30) & 1)
            blink     = bool((cell >> 31) & 1)

            fg = COLORS[fg_idx]
            bg = COLORS[bg_idx]
            if invert or (blink and blink_on):
                fg, bg = bg, fg

            glyph  = self._glyphs[char_code & 0xFF]  # font ROM is 256 glyphs
            base_x = (cell_idx % GRAPHICS_COLS) * GRAPHICS_CHAR_W
            base_y = (cell_idx // GRAPHICS_COLS) * GRAPHICS_CHAR_H

            for y in range(GRAPHICS_CHAR_H):
                row_byte = glyph[y]
                for x in range(GRAPHICS_CHAR_W):
                    bit        = (row_byte >> (GRAPHICS_CHAR_W - 1 - x)) & 1
                    color      = fg if bit else bg
                    px         = ((base_y + y) * GRAPHICS_WIDTH + (base_x + x)) * 3
                    fb[px]     = color[0]
                    fb[px + 1] = color[1]
                    fb[px + 2] = color[2]

        self.screen.blit(
            pygame.image.frombuffer(fb, (GRAPHICS_WIDTH, GRAPHICS_HEIGHT), "RGB"),
            (0, 0),
        )

    def _render_inactive(self) -> None:
        # draw a red bar and little message to indicate that graphics are disabled
        # ugly ahh code though
        pygame.draw.rect(self.screen, COLORS[2], (0, 0, GRAPHICS_WIDTH, GRAPHICS_CHAR_H))
        font = pygame.font.SysFont(None, GRAPHICS_CHAR_H + 1)
        self.screen.blit(font.render("graphics disabled", True, COLORS[0], COLORS[2]), (4, 0))

    def __str__(self) -> str:
        return f"graphics: enabled={self.enabled}"


def _load_glyphs() -> list[bytes]:
    font_path = Path(__file__).parent / "VGA8.F16"
    try:
        with open(font_path, "rb") as f:
            return [bytes(f.read(GRAPHICS_CHAR_H)) for _ in range(256)]
    except FileNotFoundError:
        logger.warning(f"VGA8.F16 not found at {font_path}, characters will not render")
        return []


def _translate_key(event: pygame.event.Event) -> int:
    """Translate a pygame KEYDOWN event to a Jaide scancode (ASCII for now)."""
    if event.unicode and ord(event.unicode) < 0x100:
        return ord(event.unicode)
    # TODO: map non-printable keys (arrows, F-keys, etc.) to extended scancodes
    return 0
