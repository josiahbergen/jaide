"""Read-only, word-addressed live memory window."""

import pygame
from pygame._sdl2 import Renderer, Texture, Window

from .bus import MemoryBus, MmioAccess
from .constants import MMIO_BASE, MMIO_END, NUM_BANKS

ROWS = 32
COLS = 16
PAGE_WORDS = ROWS * COLS
MAX_START = 0x10000 - PAGE_WORDS
REFRESH_INTERVAL = 1 / 15
PADDING = 16
BACKGROUND = (22, 25, 30)
FOREGROUND = (222, 227, 234)
MUTED = (121, 132, 147)
ACCENT = (111, 190, 255)
CHANGED = (255, 207, 105)
MMIO_READ = (126, 214, 160)
MMIO_WRITTEN = (232, 140, 206)


class MemoryView:
    def __init__(self, bus: MemoryBus):
        self.bus = bus
        self.start = 0
        self.address_text = "0000"
        self.editing = False
        self.error = ""
        self.font = pygame.font.SysFont("monospace", 16)
        self.char_width = self.font.size("0")[0]
        self.row_height = self.font.get_linesize() + 2
        self.cell_width = self.char_width * 5
        self.grid_x = PADDING + self.char_width * 7
        self.ascii_x = self.grid_x + COLS * self.cell_width + PADDING
        self.grid_y = 96
        size = (self.ascii_x + COLS * self.char_width + PADDING, self.grid_y + ROWS * self.row_height + 38)
        self.window = Window("jaide memory viewer", size=size)
        self.renderer = Renderer(self.window)
        self.surface = pygame.Surface(size)
        self.texture = Texture(self.renderer, size, streaming=True)
        self.input_rect = pygame.Rect(PADDING + 7 * self.char_width, 12, 9 * self.char_width, self.row_height + 10)
        self._last_draw = 0.0
        self._previous: tuple[int | MmioAccess | None, ...] | None = None
        self._context: tuple[int, int] | None = None
        self._changed_until = [0.0] * PAGE_WORDS
        self._scroll_remainder = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            scroll = self._scroll_remainder - event.precise_y
            rows = int(scroll)
            if rows:
                self._set_start(self.start + rows * COLS)
                self.editing = False
            self._scroll_remainder = scroll - rows
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.editing = self.input_rect.collidepoint(event.pos)
            if self.editing:
                self.address_text = ""
                self.error = ""
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.editing = False
            self.address_text = f"{self.start:04X}"
            self.error = ""
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self._set_start(self.start + (-PAGE_WORDS if event.key == pygame.K_PAGEUP else PAGE_WORDS))
            elif event.key == pygame.K_ESCAPE:
                self.editing = False
                self.address_text = f"{self.start:04X}"
                self.error = ""
            elif self.editing:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    try:
                        address = int(self.address_text, 16)
                        if not 0 <= address <= 0xFFFF:
                            raise ValueError
                    except ValueError:
                        self.error = "Enter a hex address from 0000 to FFFF"
                    else:
                        self._set_start(address)
                        self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.address_text = self.address_text[:-1]
                    self.error = ""
                elif event.unicode and event.unicode in "0123456789abcdefABCDEFxX" and len(self.address_text) < 6:
                    self.address_text += event.unicode.upper()
                    self.error = ""
        self._last_draw = 0.0

    def _set_start(self, address: int) -> None:
        self.start = max(0, min(MAX_START, address))
        self.address_text = f"{self.start:04X}"
        self.error = ""
        self._scroll_remainder = 0.0

    def _text(self, text: str, x: int, y: int, color=FOREGROUND) -> None:
        self.surface.blit(self.font.render(text, True, color), (x, y))

    def draw(self, now: float) -> None:
        if now - self._last_draw < REFRESH_INTERVAL:
            return
        self._last_draw = now
        bank = self.bus.current_bank() % (NUM_BANKS + 1)
        context = (self.start, bank)
        # mmio cells hold the most recent access instead of a word, since reading mmio has side effects
        words = tuple(
            self.bus.mmio_accesses[address - MMIO_BASE] if MMIO_BASE <= address <= MMIO_END else self.bus.peek16(address, bank=bank)
            for address in range(self.start, self.start + PAGE_WORDS)
        )
        if context != self._context:
            self._previous = None
            self._changed_until = [0.0] * PAGE_WORDS
        if self._previous is not None:
            for offset, (old, new) in enumerate(zip(self._previous, words)):
                if old != new:
                    self._changed_until[offset] = now + 0.5
        self._previous = words
        self._context = context

        self.surface.fill(BACKGROUND)
        self._text("Start:", PADDING, 18)
        pygame.draw.rect(self.surface, ACCENT if self.editing else MUTED, self.input_rect, width=1, border_radius=3)
        self._text(self.address_text + ("_" if self.editing else ""), self.input_rect.x + 7, 18, ACCENT)
        self._text(f"{self.start:04X}–{self.start + PAGE_WORDS - 1:04X}   Bank: {bank:02X}   512 words", self.input_rect.right + 24, 18)
        self._text(self.error or "Click start + Enter to jump · Scroll for rows · PgUp/PgDn for pages", PADDING, 49, CHANGED if self.error else MUTED)
        for col in range(COLS):
            self._text(f"  +{col:X}", self.grid_x + col * self.cell_width, self.grid_y - self.row_height, MUTED)
        self._text("ASCII", self.ascii_x, self.grid_y - self.row_height, MUTED)
        for row in range(ROWS):
            address = self.start + row * COLS
            y = self.grid_y + row * self.row_height
            if row % 2 == 0:
                pygame.draw.rect(self.surface, (28, 32, 38), (PADDING - 4, y, self.surface.get_width() - 2 * PADDING + 8, self.row_height))
            self._text(f"{address:04X}:", PADDING, y, ACCENT)
            for col in range(COLS):
                offset = row * COLS + col
                word = words[offset]
                if word is None:
                    self._text("----", self.grid_x + col * self.cell_width, y, MUTED)
                    self._text("-", self.ascii_x + col * self.char_width, y, MUTED)
                    continue
                if isinstance(word, MmioAccess):
                    color = MMIO_WRITTEN if word.written else MMIO_READ
                    word = word.value
                else:
                    color = FOREGROUND
                if self._changed_until[offset] > now:
                    color = CHANGED
                self._text(f"{word:04X}", self.grid_x + col * self.cell_width, y, color)
                self._text(chr(word) if 0x20 <= word <= 0x7E else ".", self.ascii_x + col * self.char_width, y, color)
        pygame.draw.line(self.surface, MUTED, (self.ascii_x - PADDING, self.grid_y - self.row_height), (self.ascii_x - PADDING, self.grid_y + ROWS * self.row_height))
        legend_y = self.surface.get_height() - 27
        legend = [
            ("Amber: changed · MMIO ", MUTED),
            ("green: last read", MMIO_READ),
            (" · ", MUTED),
            ("pink: last written", MMIO_WRITTEN),
            (" · ----: untouched · Follows current bank", MUTED),
        ]
        x = PADDING
        for text, color in legend:
            self._text(text, x, legend_y, color)
            x += self.font.size(text)[0]
        self.texture.update(self.surface)
        self.renderer.clear()
        self.texture.draw()
        self.renderer.present()

    def close(self) -> None:
        del self.texture, self.renderer
        self.window.destroy()
