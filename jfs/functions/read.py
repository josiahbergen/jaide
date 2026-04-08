import os
import sys
from array import array

from ..constants import BLOCK_SIZE, BOOT_INDICES, EOF, MAGIC, ROOT_ENTRIES, ROOT_ENTRY_SIZE
from ..util import JFSArgs, block_offset, decode_packed_null_terminated, logger


def _words_to_bytes_le(words: array) -> bytearray:
    out = bytearray()
    for w in words:
        out.append(w & 0xFF)
        out.append((w >> 8) & 0xFF)
    return out


def read_file(args: JFSArgs) -> None:
    scope = "read.py:read_file()"

    if not args.files or len(args.files) != 1:
        logger.fatal("read requires exactly one file via -f/--files", scope)

    image_path = os.path.abspath(args.image)
    if not os.path.exists(image_path):
        logger.fatal(f"image file {image_path} does not exist.", scope)

    requested = os.path.basename(args.files[0])
    if "." in requested:
        req_name, req_ext = requested.split(".", 1)
    else:
        req_name, req_ext = requested, ""

    req_name = req_name.strip()
    req_ext = req_ext.strip()

    with open(image_path, "rb") as f:
        disk = array("H")
        disk.frombytes(f.read())

    if disk[BOOT_INDICES.MAGIC] != MAGIC:
        logger.fatal("file is not a valid jfs image (bad magic).", scope)

    num_blocks = disk[BOOT_INDICES.BLOCKS]
    table_start = block_offset(disk[BOOT_INDICES.TABLE_START])  # word index
    root_start = block_offset(disk[BOOT_INDICES.ROOT_START])     # word index

    start_block: int | None = None
    size_bytes: int | None = None

    for i in range(ROOT_ENTRIES):
        entry_start = root_start + i * ROOT_ENTRY_SIZE
        entry = disk[entry_start:entry_start + ROOT_ENTRY_SIZE]

        size = entry[7]
        if size == 0:
            continue

        filename = decode_packed_null_terminated(entry[0:4])
        extension = decode_packed_null_terminated(entry[4:6])

        if filename == req_name and (req_ext == "" or extension == req_ext):
            start_block = entry[6]
            size_bytes = size
            break

    if start_block is None or size_bytes is None:
        logger.fatal(f"file not found: {requested}", scope)

    if start_block >= num_blocks:
        logger.fatal(f"corrupt root entry: start block {start_block} out of range", scope)

    bytes_per_block = BLOCK_SIZE * 2
    out = bytearray()

    block = start_block
    visited: set[int] = set()
    while True:
        if block in visited:
            logger.fatal("corrupt FAT chain: loop detected", scope)
        visited.add(block)

        data_start = block_offset(block)
        block_words = disk[data_start:data_start + BLOCK_SIZE]
        out.extend(_words_to_bytes_le(block_words))

        next_block = disk[table_start + block]
        if next_block == EOF:
            break
        if next_block >= num_blocks:
            logger.fatal(f"corrupt FAT chain: next block {next_block} out of range", scope)
        block = next_block

        # minor efficiency: stop once we've collected enough
        if len(out) >= size_bytes + bytes_per_block:
            break

    out = out[:size_bytes]

    try:
        sys.stdout.buffer.write(out)
    except Exception:
        # fallback: best-effort text output
        sys.stdout.write(out.decode("utf-8", errors="replace"))
