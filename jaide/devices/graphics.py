import tkinter as tk
from PIL import Image, ImageTk

WIDTH  = 80
HEIGHT = 25
GLYPH_WIDTH = 8
GLYPH_HEIGHT = 16
FPS_MS = 33

COLORS = [
    (0, 0, 0),       # black
    (255, 255, 255), # white
    (255, 0, 0),     # red
    (0, 255, 0),     # green
    (0, 0, 255),     # blue
    (255, 255, 0),   # yellow
    (0, 255, 255),   # cyan
    (255, 0, 255),   # magenta
    (128, 128, 128), # gray
    (128, 0, 0),     # dark red
    (0, 128, 0),     # dark green
    (0, 0, 128),     # dark blue
    (128, 128, 0),   # dark yellow
    (0, 128, 128),   # dark cyan
    (128, 0, 128),   # dark magenta
]

GLYPHS = [
    [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], # space
    [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF], # block
]

class Graphics:
    def __init__(self, vram: memoryview):
        self.vram = vram
        self.framebuf: list[int] = [0] * (WIDTH * GLYPH_WIDTH * HEIGHT * GLYPH_HEIGHT * 3) # 3 bytes per pixel (RGB)
        self._last_hash = None

        self.root = tk.Tk()
        self.root.title("jaide video controller output (80x25 chars)")
        self.root.geometry(f"{WIDTH * GLYPH_WIDTH}x{HEIGHT * GLYPH_HEIGHT }")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.label = tk.Label(self.root, bg="black")
        self.label.pack()

        self.photo = None
        # Update the window to ensure Tkinter is fully initialized before PIL tries to use it
        self.root.update_idletasks()
        self._tick()

    def _tick(self):
        self._render_frame()
        h = hash(bytes(self.framebuf))

        if h != self._last_hash:
            print(f"rendering frame")
            self._last_hash = h
            img = Image.frombuffer("RGB", (WIDTH * GLYPH_WIDTH, HEIGHT * GLYPH_HEIGHT), bytes(self.framebuf), "raw")
            # img = img.resize((WIDTH * SCALE, HEIGHT * SCALE), Image.Resampling.NEAREST)

            self.photo = ImageTk.PhotoImage(img)
            self.label.configure(image=self.photo)

        self.root.after(FPS_MS, self._tick)


    def _render_frame(self):
        # word-addressed: 2 bytes per character
        for char_idx in range(WIDTH * HEIGHT):
            i = char_idx * 2
            lo, hi = self.vram[i], self.vram[i + 1]
            fore, back = self._parse_attrs(hi)
            self._draw_glyph(GLYPHS[lo], fore, back, char_idx // WIDTH, char_idx % WIDTH)

    def _draw_glyph(self, glyph: list[int], fore: tuple[int, int, int], back: tuple[int, int, int], char_row: int, char_col: int):
        # Calculate the base pixel position for this character
        base_y = char_row * GLYPH_HEIGHT
        base_x = char_col * GLYPH_WIDTH
        for y in range(GLYPH_HEIGHT):
            for x in range(GLYPH_WIDTH):
                self.framebuf[(base_y + y) * WIDTH * GLYPH_WIDTH * 3 + (base_x + x) * 3 + 0] = fore[0]
                self.framebuf[(base_y + y) * WIDTH * GLYPH_WIDTH * 3 + (base_x + x) * 3 + 1] = fore[1]
                self.framebuf[(base_y + y) * WIDTH * GLYPH_WIDTH * 3 + (base_x + x) * 3 + 2] = fore[2]

    def _parse_attrs(self, byte: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        fore = byte & 0b1111
        back = (byte >> 4) & 0b111
        blink = (byte >> 7) & 1
        fore = back if blink else fore
        return (COLORS[fore], COLORS[back])

    def close(self):
        self.root.destroy()
