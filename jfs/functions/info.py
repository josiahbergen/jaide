# info.py
# functions for inspecting image files.
# josiah bergen, april 2026

import os
from array import array

from ..constants import BLOCK_SIZE, BOOT_INDICES, MAGIC, ROOT_ENTRIES, ROOT_ENTRY_SIZE
from ..util import JFSArgs, block_offset, decode_packed_null_terminated, logger


def get_image_info(args: JFSArgs) -> None:
    """ Get information about an image file. """
    scope = "info.py:get_image_info()"

    image_file = args.image
    image_path = os.path.abspath(image_file)

    # check if file exists
    if not os.path.exists(image_path):
        logger.fatal(f"image file {image_path} does not exist.", scope)

    # read contents
    with open(image_path, "rb") as f:
        image_contents = array('H', f.read())

    # verify magic number
    if image_contents[BOOT_INDICES.MAGIC] != MAGIC:
        logger.error(f"magic: expected 0x{MAGIC:04X}, got 0x{image_contents[BOOT_INDICES.MAGIC]:04X}", scope)
        logger.fatal(f"file is not a valid jfs image.", scope, newline=False)

    # print the block count
    num_blocks = image_contents[BOOT_INDICES.BLOCKS]

    print(f"jaidefs disk image: {num_blocks} blocks ({num_blocks * BLOCK_SIZE * 2 // 1024} KiB)")

    file_list: list[str] = []

    root_start_block = image_contents[BOOT_INDICES.ROOT_START]
    root_start = block_offset(root_start_block)

    for i in range(ROOT_ENTRIES):
        entry_start = root_start + i * ROOT_ENTRY_SIZE
        entry = image_contents[entry_start:entry_start + ROOT_ENTRY_SIZE]

        name_data = entry[0:4]
        ext_data = entry[4:6]
        start_block = entry[6]
        size = entry[7]

        if size == 0:
            # empty entry
            continue

        filename = decode_packed_null_terminated(name_data)
        extension = decode_packed_null_terminated(ext_data)

        file_size = size * 2  # convert words to kibibytes

        file_list.append(f"{filename}.{extension} ({file_size} bytes) at block {start_block}")
    
    print("\n".join(file_list) if file_list else "no files found.")