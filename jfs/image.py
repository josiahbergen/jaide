# image.py
# a jfs volume held in memory. implements the format in docs/software/jfs.md.
# josiah bergen, april 2026

import sys
from array import array
from dataclasses import dataclass

BLOCK_WORDS = 256

MAGIC = 0x333A

# boot block word indices
BOOT_MAGIC        = 0
BOOT_BLOCKS       = 1
BOOT_TABLE_START  = 2
BOOT_TABLE_BLOCKS = 3
BOOT_ROOT_START   = 4
BOOT_ROOT_BLOCKS  = 5
BOOT_DATA_START   = 6

# allocation table values
FREE     = 0x0000
RESERVED = 0xFFFE
END      = 0xFFFF

# root directory entry
ENTRY_WORDS = 16
ENTRY_START = 14
ENTRY_SIZE  = 15
NAME_LENGTH = 13  # characters; the 14-word name field always keeps a terminating zero

MAX_FILE_WORDS = 0xFFFF

# geometry of newly created volumes
NEW_BLOCKS      = 2048
NEW_ROOT_BLOCKS = 2


class JfsError(Exception):
    """the image is not valid jfs, or the requested operation is impossible."""


def blocks_for(words: int) -> int:
    """number of blocks needed to hold a number of words"""
    return -(-words // BLOCK_WORDS)


@dataclass(frozen=True, slots=True)
class File:
    """one used root directory entry"""

    name: str
    start: int  # first block, or END for an empty file
    size: int   # words


class Image:
    """
    A jfs volume: a flat array of words, plus the operations the format defines on it.

    Every read goes through the boot block's header, so an Image works on any valid
    volume, not just ones this tool created.
    """

    def __init__(self, words: array):
        self.words = words
        self._validate()

    # construction and persistence

    @classmethod
    def create(cls) -> "Image":
        """a new, empty volume"""
        table_blocks = blocks_for(NEW_BLOCKS)
        root_start = 1 + table_blocks
        data_start = root_start + NEW_ROOT_BLOCKS

        words = array("H", bytes(NEW_BLOCKS * BLOCK_WORDS * 2))
        words[BOOT_MAGIC]        = MAGIC
        words[BOOT_BLOCKS]       = NEW_BLOCKS
        words[BOOT_TABLE_START]  = 1
        words[BOOT_TABLE_BLOCKS] = table_blocks
        words[BOOT_ROOT_START]   = root_start
        words[BOOT_ROOT_BLOCKS]  = NEW_ROOT_BLOCKS
        words[BOOT_DATA_START]   = data_start

        # the boot, table, and root blocks belong to no file
        table = BLOCK_WORDS
        words[table : table + data_start] = array("H", [RESERVED] * data_start)

        return cls(words)

    @classmethod
    def load(cls, path: str) -> "Image":
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            raise JfsError(f"cannot read {path}: {e.strerror}") from e

        if len(data) % 2:
            raise JfsError(f"{path} is not a whole number of words")
        return cls(words_from_bytes(data))

    def save(self, path: str) -> None:
        try:
            with open(path, "wb") as f:
                f.write(words_to_bytes(self.words))
        except OSError as e:
            raise JfsError(f"cannot write {path}: {e.strerror}") from e

    # geometry, straight from the header

    @property
    def blocks(self) -> int:
        return self.words[BOOT_BLOCKS]

    @property
    def table_start(self) -> int:
        return self.words[BOOT_TABLE_START]

    @property
    def table_blocks(self) -> int:
        return self.words[BOOT_TABLE_BLOCKS]

    @property
    def root_start(self) -> int:
        return self.words[BOOT_ROOT_START]

    @property
    def root_blocks(self) -> int:
        return self.words[BOOT_ROOT_BLOCKS]

    @property
    def data_start(self) -> int:
        return self.words[BOOT_DATA_START]

    @property
    def root_entries(self) -> int:
        return self.root_blocks * BLOCK_WORDS // ENTRY_WORDS

    def _validate(self) -> None:
        words = self.words
        if len(words) < BLOCK_WORDS or words[BOOT_MAGIC] != MAGIC:
            raise JfsError("not a jfs image (bad magic)")
        if not 0 < self.blocks <= RESERVED:
            raise JfsError(f"header: invalid block count {self.blocks}")
        if len(words) != self.blocks * BLOCK_WORDS:
            raise JfsError(f"header says {self.blocks} blocks, but the image holds {len(words) / BLOCK_WORDS:g}")

        expected = {
            "table start": (self.table_start, 1),
            "table blocks": (self.table_blocks, blocks_for(self.blocks)),
            "root start": (self.root_start, self.table_start + self.table_blocks),
            "data start": (self.data_start, self.root_start + self.root_blocks),
        }
        for field, (actual, wanted) in expected.items():
            if actual != wanted:
                raise JfsError(f"header: {field} is {actual}, expected {wanted}")
        if self.root_blocks == 0 or self.data_start > self.blocks:
            raise JfsError("header: the root directory is empty or runs past the end of the volume")

    # allocation table

    def _table(self, block: int) -> int:
        """word index of a block's allocation table entry"""
        return self.table_start * BLOCK_WORDS + block

    def free_blocks(self) -> list[int]:
        return [block for block in range(self.blocks) if self.words[self._table(block)] == FREE]

    def chain(self, file: File) -> list[int]:
        """the blocks of a file, in order"""
        blocks: list[int] = []
        block = file.start
        for _ in range(blocks_for(file.size)):
            if not self.data_start <= block < self.blocks:
                raise JfsError(f"{file.name}: corrupt chain (block {block:#06x} is not a data block)")
            blocks.append(block)
            block = self.words[self._table(block)]
        if block != END:
            raise JfsError(f"{file.name}: corrupt chain (longer than the file's {file.size} words)")
        return blocks

    # root directory

    def _entry(self, index: int) -> int:
        """word index of a root directory entry"""
        return self.root_start * BLOCK_WORDS + index * ENTRY_WORDS

    def files(self) -> list[File]:
        files: list[File] = []
        for index in range(self.root_entries):
            entry = self.words[self._entry(index) : self._entry(index) + ENTRY_WORDS]
            if entry[0] == 0:
                continue
            name = "".join(chr(word) for word in entry[:ENTRY_START]).split("\0")[0]
            files.append(File(name, entry[ENTRY_START], entry[ENTRY_SIZE]))
        return files

    def find(self, name: str) -> File:
        for file in self.files():
            if file.name == name:
                return file
        raise JfsError(f"no file named {name}")

    # files

    def read(self, name: str) -> array:
        """the contents of a file, as words"""
        file = self.find(name)
        contents = array("H")
        for block in self.chain(file):
            contents.extend(self.words[block * BLOCK_WORDS : (block + 1) * BLOCK_WORDS])
        return contents[: file.size]

    def add(self, name: str, contents: array) -> File:
        """store a new file"""
        if not 1 <= len(name) <= NAME_LENGTH:
            raise JfsError(f"{name!r}: names are 1 to {NAME_LENGTH} characters")
        if not all(0x21 <= ord(char) <= 0x7E for char in name):
            raise JfsError(f"{name!r}: names are printable ascii with no spaces")
        if any(file.name == name for file in self.files()):
            raise JfsError(f"{name}: already exists")
        if len(contents) > MAX_FILE_WORDS:
            raise JfsError(f"{name}: {len(contents)} words is larger than the {MAX_FILE_WORDS} word limit")

        index = next((i for i in range(self.root_entries) if self.words[self._entry(i)] == 0), None)
        if index is None:
            raise JfsError(f"{name}: the root directory is full ({self.root_entries} files)")

        needed = blocks_for(len(contents))
        blocks = self.free_blocks()[:needed]
        if len(blocks) < needed:
            raise JfsError(f"{name}: needs {needed} blocks, but only {len(blocks)} are free")

        # contents, with the unused tail of the last block zeroed
        padded = contents + array("H", [0] * (needed * BLOCK_WORDS - len(contents)))
        for i, block in enumerate(blocks):
            self.words[block * BLOCK_WORDS : (block + 1) * BLOCK_WORDS] = padded[i * BLOCK_WORDS : (i + 1) * BLOCK_WORDS]
            self.words[self._table(block)] = blocks[i + 1] if i + 1 < needed else END

        file = File(name, blocks[0] if blocks else END, len(contents))
        entry = self._entry(index)
        self.words[entry : entry + ENTRY_WORDS] = array("H", [*name.encode("ascii").ljust(ENTRY_START, b"\0"), file.start, file.size])
        return file


# words on the host are two bytes each, low byte first

def words_from_bytes(data: bytes) -> array:
    words = array("H", data)
    if sys.byteorder == "big":
        words.byteswap()
    return words


def words_to_bytes(words: array) -> bytes:
    if sys.byteorder == "big":
        words = array("H", words)
        words.byteswap()
    return words.tobytes()
