import tkinter as tk
from PIL import Image, ImageTk
import threading

from ..emulator import Emulator

WIDTH  = 80
HEIGHT = 25
GLYPH_WIDTH = 8
GLYPH_HEIGHT = 16
FPS_MS = 33

COLORS = [
    (0, 0, 0),       # 0: black
    (255, 255, 255), # 1: white
    (255, 0, 0),     # 2: red
    (0, 255, 0),     # 3: green
    (0, 0, 255),     # 4: blue
    (255, 255, 0),   # 5: yellow
    (0, 255, 255),   # 6: cyan
    (255, 0, 255),   # 7: purple
    (128, 128, 128), # 8: gray
    (192, 192, 192), # 9: light gray
    (128, 0, 0),     # 10: dark red
    (0, 128, 0),     # 11: dark green
    (0, 0, 128),     # 12: dark blue
    (128, 128, 0),   # 13: dark yellow
    (0, 128, 128),   # 14: dark cyan
    (128, 0, 128),   # 15: dark magenta
]

class Graphics(threading.Thread):

    def __init__(self, vram: memoryview, emulator: Emulator):
        super().__init__(daemon=True)
        self.vram = vram # memoryview of vram
        self.emulator = emulator # emulator instance

        self.root = tk.Tk()
        self.root.title("jaide video controller output")
        self.root.geometry(f"{WIDTH * GLYPH_WIDTH}x{HEIGHT * GLYPH_HEIGHT}")

        # load glyphs
        # this sucks, ideally we would pass in glyphs as a bytearray or something
        try:
            with open("jaide/devices/VGA8.F16", "rb") as f:
                self.glyphs = [bytes(f.read(16)) for _ in range(256)]
        except FileNotFoundError:
            print("Graphics process: VGA8.F16 not found")
            return

        self.framebuf = [0] * (WIDTH * GLYPH_WIDTH * HEIGHT * GLYPH_HEIGHT * 3)
        self.label = tk.Label(self.root, bg="black") # what we render to
        self.label.pack()
        
        self.root.bind("<Key>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.last_hash = None
        self.photo = None
        self.closed = False

        # run the thing!
        self.render()


    def on_key(self, event):
        if event.char:
                self.emulator.ports[1] = ord(event.char)
                self.emulator.request_interrupt(4)

    def close(self):
        self.closed = True
        self.root.destroy()


    def render(self):
        if self.closed:
            return

        def parse_attrs(byte: int):
            fore = byte & 0b1111
            back = (byte >> 4) & 0b1111
            return (COLORS[fore], COLORS[back])

        def draw_glyph(glyph: bytes, fore, back, char_row, char_col):
            base_y = char_row * GLYPH_HEIGHT
            base_x = char_col * GLYPH_WIDTH

            for y in range(GLYPH_HEIGHT):
                row_byte = glyph[y]
                for x in range(GLYPH_WIDTH):
                    bit = (row_byte >> (GLYPH_WIDTH - 1 - x)) & 1
                    color = fore if bit else back
                    pixel_idx = ((base_y + y) * WIDTH * GLYPH_WIDTH + (base_x + x)) * 3
                    self.framebuf[pixel_idx + 0] = color[0]
                    self.framebuf[pixel_idx + 1] = color[1]
                    self.framebuf[pixel_idx + 2] = color[2]

        # hash to check if VRAM changed
        current_data = bytes(self.vram[:WIDTH * HEIGHT * 2]) # read only relevant part
        h = hash(current_data)
        
        if h != self.last_hash:
            self.last_hash = h
            
            # render
            for char_idx in range(WIDTH * HEIGHT):
                i = char_idx * 2
                lo, hi = self.vram[i], self.vram[i + 1]
                fore, back = parse_attrs(hi)
                draw_glyph(self.glyphs[lo], fore, back, char_idx // WIDTH, char_idx % WIDTH)
            
            img = Image.frombuffer("RGB", (WIDTH * GLYPH_WIDTH, HEIGHT * GLYPH_HEIGHT), bytes(self.framebuf), "raw")
            photo = ImageTk.PhotoImage(img)
            self.label.configure(image=photo)
            self.photo = photo # keep reference

        # run again in 33ms (30fps)
        self.root.after(FPS_MS, self.render)

