# create.py
# functions for creating image files.
# josiah bergen, april 2026

import os
from array import array
from math import ceil

from ..constants import BLOCK_SIZE, BLOCKS, BOOT_INDICES, EOF, MAGIC, ROOT_ENTRIES, ROOT_ENTRY_SIZE, UNALLOCATED
from ..util import JFSArgs, block_offset, logger


def generate_root_table_entry(file_name: str, file_ext: str, file_len: int, start_block: int) -> array:
    logger.verbose(f"generating root entry for {file_name}.{file_ext}...")

    file_name = file_name.ljust(8, "\x00")  # pad with zeros
    file_ext = file_ext.ljust(4, "\x00")

    # pack filename: 2 ascii chars per word, little-endian (first char in low byte)
    # extension is the same as filename
    name_words = [ord(file_name[i]) | (ord(file_name[i + 1]) << 8) for i in range(0, 8, 2)]
    ext_words = [ord(file_ext[0]) | (ord(file_ext[1]) << 8), ord(file_ext[2]) | (ord(file_ext[3]) << 8)]

    entry = array('H', name_words + ext_words + [start_block, file_len])
    return entry


def add_file(disk: array[int], file: str) -> None:
    scope = "create.py:add_file()"
    logger.debug(f"adding file: {file}")

    # figure out where to write the entry (and if there is even space)
    # first find the block where the root table starts
    root_start = block_offset(disk[BOOT_INDICES.ROOT_START])
    file_index = -1

    for n in range(ROOT_ENTRIES):
        entry_start = root_start + (n * ROOT_ENTRY_SIZE)
        entry = disk[entry_start:entry_start + ROOT_ENTRY_SIZE]
        if entry[0] == 0:
            file_index = n
            break
    else:
        logger.fatal(f"root directory table is full, cannot add file {file}", scope)

    # metadata and other stuff
    file_name: str = "".join(os.path.basename(file).split(".")[:1])
    file_ext: str = os.path.basename(file).split(".")[-1]
    file_contents = open(file, "rb").read()
    file_len = len(file_contents)  # words
    blocks_needed = ceil(file_len / BLOCK_SIZE)

    if len(file_name) > 8: logger.fatal(f"file name {file_name} is too long for max 8 characters", scope)
    if len(file_ext)  > 4: logger.fatal(f"file extension {file_ext} is too long for max 4 characters", scope)

    logger.verbose(f"{file_name}.{file_ext} is {file_len} words long, needs {blocks_needed} block{'' if blocks_needed == 1 else 's'}")

    # get list of all the blocks that the file will be stored in
    # these will be set to referece each other, and the first one
    # will be referenced in the root table entry.
    blocks: list[int] = []
    table_start = block_offset(disk[BOOT_INDICES.TABLE_START])   # word index of the start of the allocation table
    table_len   = block_offset(disk[BOOT_INDICES.TABLE_BLOCKS])  # number of entries in the allocation table
    
    for n in range(table_start, table_start + table_len):
        # loop through all entries in the allocation table
        # and search for unallocated blocks
        if disk[table_start + n] == UNALLOCATED:
            blocks.append(n)
        if len(blocks) == blocks_needed:
            break # we are done!

    logger.verbose(f"found {len(blocks)} free blocks: {", ".join([f"0x{block:02X}" for block in blocks])}")

    # use file_index to get the actual address of the root table start, 
    # plus the offset of the nth table entry (entries are 8 words long)
    entry_start = root_start + (file_index * ROOT_ENTRY_SIZE)
    start_block = blocks[0]

    # generate and write the root table entry to the disk
    entry = generate_root_table_entry(file_name, file_ext, file_len, start_block)
    disk[entry_start:entry_start + ROOT_ENTRY_SIZE] = entry
    logger.verbose(f"populated root table entry 0x{n:02X} with {" ".join([f"{word:04X}" for word in entry.tolist()])}")


    # walk the blocks and write the file contents to the disk
    for i, block in enumerate[int](blocks):

        # populate the allocation table entry for this block
        next_block = blocks[i + 1] if i + 1 < len(blocks) else EOF
        disk[table_start + block] = next_block

        # write block contents to the disk
        block_start = block_offset(block)
        block_contents = file_contents[i * BLOCK_SIZE : (i + 1) * BLOCK_SIZE]

        disk[block_start:block_start + BLOCK_SIZE] = array[int]("H", block_contents)
        logger.verbose(f"populated allocation table entry 0x{block:02X} with 0x{next_block:04X}")


def create(args: JFSArgs) -> None:
    scope = "create.py:create()"
    image = args.image
    logger.info(f"creating image at {image}...")

    table_blocks = ceil(BLOCKS / BLOCK_SIZE)   # 1 FAT entry (1 word) per block; 256 entries fit per block
    root_blocks  = 2                           # fixed per spec
    data_start   = 1 + table_blocks + root_blocks

    disk = array[int]('H', [0] * (BLOCKS * BLOCK_SIZE))

    # boot block (block 0, word indices 0..6)
    disk[BOOT_INDICES.MAGIC]        = MAGIC
    disk[BOOT_INDICES.BLOCKS]       = BLOCKS
    disk[BOOT_INDICES.TABLE_START]  = 1
    disk[BOOT_INDICES.TABLE_BLOCKS] = table_blocks
    disk[BOOT_INDICES.ROOT_START]   = 1 + table_blocks
    disk[BOOT_INDICES.ROOT_BLOCKS]  = root_blocks
    disk[BOOT_INDICES.DATA_START]   = data_start

    for file in args.files:
        if not os.path.exists(file):
            logger.fatal(f"file {file} does not exist", scope)
        
        add_file(disk, file)

    full_path = os.path.abspath(image)
    with open(full_path, "wb") as f:
        logger.verbose(f"full output path is {full_path}")
        disk.tofile(f)

    logger.success(f"wrote {BLOCKS} blocks, {BLOCKS * BLOCK_SIZE:,} words.")
