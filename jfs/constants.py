# constants.py
# constants used throughout the project.
# josiah bergen, april 2026

from enum import IntEnum, auto

from common.isa import ZeroIndexedIntEnum

MAGIC      = 0x333A  # ":3" (little-endian)
BLOCK_SIZE = 256     # words
BLOCKS     = 2048    # total number of blocks on the disk

ROOT_ENTRY_SIZE = 8  # words
ROOT_ENTRIES    = 64 # maximum number of entries in the root directory table

# allocation table special values
UNALLOCATED = 0x0000
EOF = 0xFFFF

class BOOT_INDICES(ZeroIndexedIntEnum):

    MAGIC        = auto()  # 0x3A33
    BLOCKS       = auto()  # total number of blocks on the disk  
    TABLE_START  = auto()  # block index of the first element in the table
    TABLE_BLOCKS = auto()  # number of blocks in the allocation table
    ROOT_START   = auto()  # block index of the first root block
    ROOT_BLOCKS  = auto()  # number of blocks in the root directory
    DATA_START   = auto()  # block index of the first data block
    