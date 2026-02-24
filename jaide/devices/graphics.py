import tkinter as tk
from multiprocessing import shared_memory, Queue
from typing import Any
from PIL import Image, ImageTk

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

from multiprocessing import Process

def start_graphics() -> tuple[Process, shared_memory.SharedMemory, Any]:
    shm = shared_memory.SharedMemory(create=True, size=0x8000)
    q = Queue()
    p = Process(target=run_graphics_process, args=(shm.name, q))
    p.start()
    return p, shm, q

def run_graphics_process(shm_name: str, input_queue: Any):
    """
    Entry point for the graphics process.
    """
    try:
        shm = shared_memory.SharedMemory(name=shm_name)
        vram = shm.buf
        
        root = tk.Tk()
        root.title("jaide video controller output")
        root.geometry(f"{WIDTH * GLYPH_WIDTH}x{HEIGHT * GLYPH_HEIGHT}")
        
        # load glyphs. 
        # this sucks, ideally we would pass in glyphs as a bytearray or something
        try:
            with open("jaide/devices/VGA8.F16", "rb") as f:
                glyphs = [bytes(f.read(16)) for _ in range(256)]
        except FileNotFoundError:
            print("Graphics process: VGA8.F16 not found")
            return

        framebuf = [0] * (WIDTH * GLYPH_WIDTH * HEIGHT * GLYPH_HEIGHT * 3)
        label = tk.Label(root, bg="black")
        label.pack()
        
        # State
        state = {
            "last_hash": None,
            "photo": None,
            "closed": False
        }

        def on_key(event):
            if event.char:
                input_queue.put(("key", event.char))

        root.bind("<Key>", on_key)
        
        def close():
            state["closed"] = True
            root.destroy()
            
        root.protocol("WM_DELETE_WINDOW", close)

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
                    framebuf[pixel_idx + 0] = color[0]
                    framebuf[pixel_idx + 1] = color[1]
                    framebuf[pixel_idx + 2] = color[2]

        def tick():
            if state["closed"]:
                return

            # hash to check if VRAM changed
            current_data = bytes(vram[:WIDTH * HEIGHT * 2]) # read only relevant part
            h = hash(current_data)
            
            if h != state["last_hash"]:
                state["last_hash"] = h
                
                # render
                for char_idx in range(WIDTH * HEIGHT):
                    i = char_idx * 2
                    lo, hi = vram[i], vram[i + 1]
                    fore, back = parse_attrs(hi)
                    draw_glyph(glyphs[lo], fore, back, char_idx // WIDTH, char_idx % WIDTH)
                
                img = Image.frombuffer("RGB", (WIDTH * GLYPH_WIDTH, HEIGHT * GLYPH_HEIGHT), bytes(framebuf), "raw")
                photo = ImageTk.PhotoImage(img)
                label.configure(image=photo)
                state["photo"] = photo # keep reference

            # tick every 33ms (30fps)
            root.after(FPS_MS, tick)

        tick()
        root.mainloop()
        
    except Exception as e:
        print(f"Graphics process error: {e}")
