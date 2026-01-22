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
    (192, 192, 192), # light gray
    (128, 0, 0),     # dark red
    (0, 128, 0),     # dark green
    (0, 0, 128),     # dark blue
    (128, 128, 0),   # dark yellow
    (0, 128, 128),   # dark cyan
    (128, 0, 128),   # dark magenta
]

class Graphics:
    def __init__(self, vram: memoryview):
        self.vram = vram
        self.framebuf: list[int] = [0] * (WIDTH * GLYPH_WIDTH * HEIGHT * GLYPH_HEIGHT * 3) # 3 bytes per pixel (RGB)
        
        # insane hard-coded filepath and glyph count/size but whatever
        with open("jaide/devices/VGA8.F16", "rb") as f:
            self.glyphs = [bytes(f.read(16)) for _ in range(256)]
        print(f"loaded {len(self.glyphs)} glyphs to character rom")
        
        self._last_hash = None
        self._after_id = None
        self._closed = False

        self.root = tk.Tk()
        self.root.title("jaide video controller output")
        self.root.geometry(f"{WIDTH * GLYPH_WIDTH}x{HEIGHT * GLYPH_HEIGHT }")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.label = tk.Label(self.root, bg="black")
        self.label.pack()

        self.photo = None
        print("graphics controller initialized")
        self._tick()

    def _tick(self):
        if self._closed:
            return
        
        try:
            if not self.root.winfo_exists():
                self._closed = True
                return
        except tk.TclError:
            self._closed = True
            return

        h = hash(bytes(self.vram))

        if h != self._last_hash:
            self._last_hash = h
            self._render_frame()
            img = Image.frombuffer("RGB", (WIDTH * GLYPH_WIDTH, HEIGHT * GLYPH_HEIGHT), bytes(self.framebuf), "raw")

            self.photo = ImageTk.PhotoImage(img)
            self.label.configure(image=self.photo)

        if not self._closed:
            self._after_id = self.root.after(FPS_MS, self._tick)


    def _render_frame(self):
        # word-addressed: 2 bytes per character
        for char_idx in range(WIDTH * HEIGHT):
            i = char_idx * 2
            lo, hi = self.vram[i], self.vram[i + 1]
            fore, back = self._parse_attrs(hi)

            # if hi != 0:
            #     print(f"drawing glyph {lo:02X} at {char_idx // WIDTH}, {char_idx % WIDTH}. color: {hi:02X}, fore: {fore}, back: {back}")
            self._draw_glyph(self.glyphs[lo], fore, back, char_idx // WIDTH, char_idx % WIDTH)

    def _draw_glyph(self, glyph: bytes, fore: tuple[int, int, int], back: tuple[int, int, int], char_row: int, char_col: int):
        # Convert integer to 16 bytes (big-endian
        base_y = char_row * GLYPH_HEIGHT
        base_x = char_col * GLYPH_WIDTH

        for y in range(GLYPH_HEIGHT):
            row_byte = glyph[y]
            for x in range(GLYPH_WIDTH):
                # Bit 7 is leftmost pixel, bit 0 is rightmost
                bit = (row_byte >> (GLYPH_WIDTH - 1 - x)) & 1
                color = fore if bit else back
                pixel_idx = ((base_y + y) * WIDTH * GLYPH_WIDTH + (base_x + x)) * 3
                self.framebuf[pixel_idx + 0] = color[0]
                self.framebuf[pixel_idx + 1] = color[1]
                self.framebuf[pixel_idx + 2] = color[2]

    def _parse_attrs(self, byte: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        fore = byte & 0b1111
        back = (byte >> 4) & 0b1111
        return (COLORS[fore], COLORS[back])

    def close(self):
        self._closed = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass  # Window already destroyed
        self.root.destroy()
