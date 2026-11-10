# jfs (jaide file system)

jfs is a fat-style filesystem with a single flat directory. this document is the format's specification; the `jfs` tool ([jfs/image.py](../../jfs/image.py)) and the kernel both implement it.

## units

everything in jfs is measured in 16-bit words. there are no bytes anywhere in the format: sizes, offsets, and file contents are all words.

- a **block** is 256 words. block `n` starts at word `n * 256` of the volume.
- a **volume** is a whole number of blocks. block indices are absolute: block 0 is the first block of the volume.
- a **file** is a sequence of words. text is stored one character per word, exactly as strings are held in memory, so a text file can be printed and a program can be executed straight from its blocks with no unpacking.

a disk image is the volume's words in order, each stored as two bytes, low byte first.

## layout

| region           | size (blocks)  | contents                         |
| ---------------- | -------------- | -------------------------------- |
| boot             | 1              | the volume header                |
| allocation table | `table blocks` | one word per block of the volume |
| root directory   | `root blocks`  | file entries                     |
| data             | the rest       | file contents                    |

the regions appear in this order with no gaps: `table start` is 1, `root start` is `table start + table blocks`, and `data start` is `root start + root blocks`.

## boot block

block 0 holds the volume header. the header is authoritative: readers take the volume's geometry from it and assume nothing else.

| word | name         | description                                                    |
| ---- | ------------ | -------------------------------------------------------------- |
| 0    | magic        | `0x333A` (the bytes `3A 33` on disk, which read `:3`)          |
| 1    | blocks       | total number of blocks in the volume, at most `0xFFFE`         |
| 2    | table start  | block index of the first allocation table block                |
| 3    | table blocks | number of allocation table blocks: `blocks / 256`, rounded up  |
| 4    | root start   | block index of the first root directory block                  |
| 5    | root blocks  | number of root directory blocks                                |
| 6    | data start   | block index of the first data block                            |

words 7 to 255 are zero.

## allocation table

the allocation table has one word for every block in the volume, indexed by absolute block index: the entry for block `n` is word `n` of the table. table words past the last block are zero.

| value               | meaning                                              |
| ------------------- | ---------------------------------------------------- |
| `0x0000`            | free                                                 |
| `0xFFFE`            | reserved: a boot, allocation table, or root block    |
| `0xFFFF`            | in use, and the last block of its file               |
| any other value     | in use; the value is the index of the file's next block |

a block is free exactly when its entry is `0x0000`, so an allocator needs no knowledge of the layout. a next-block value always names a data block.

## root directory

the root directory is an array of 16-word entries, 16 to a block, so a volume holds up to `root blocks * 16` files.

| word | size (words) | name        | description                                         |
| ---- | ------------ | ----------- | --------------------------------------------------- |
| 0    | 14           | name        | the file name, one character per word, zero-filled  |
| 14   | 1            | start block | index of the file's first block                     |
| 15   | 1            | size        | length of the file in words                         |

an entry is free exactly when the first word of its name is zero. free and used entries may appear in any order, so a reader must examine every entry.

### names

a name is 1 to 13 characters. the unused words of the name field are zero, so the field always holds a null-terminated string and can be compared with an ordinary string comparison.

characters are printable ascii other than space (`0x21` to `0x7E`). names are case-sensitive and unique within the volume. a dot has no special meaning: `demo.bin` is simply an eight-character name.

## files

a file's blocks form a chain. the chain begins at the entry's start block; each block's allocation table entry names the next, and the last block's entry is `0xFFFF`.

a file of `size` words occupies exactly `size / 256` blocks, rounded up. the words of the last block past the end of the file are zero.

an empty file has size 0 and start block `0xFFFF`. it owns no blocks.

because size is one word, a file is at most 65,535 words.

## the jfs tool

`python -m jfs` builds and inspects disk images.

| command                                                  | action                                    |
| -------------------------------------------------------- | ----------------------------------------- |
| `jfs create IMAGE [--binary FILE ...] [--text FILE ...]` | write a new image holding the given files |
| `jfs add IMAGE [--binary FILE ...] [--text FILE ...]`    | add files to an existing image            |
| `jfs info IMAGE`                                         | print the volume's geometry and its files |
| `jfs read IMAGE NAME [--text]`                           | write a file's contents to stdout         |

a host file is a stream of bytes, so the tool must be told how to turn it into words:

- `--binary` files already hold words, two bytes each, low byte first. this is what the assembler writes. the file must have an even number of bytes.
- `--text` files become one word per byte.

`read` reverses the same conversions: it writes two bytes per word, or with `--text`, one byte per word.

a file is stored under its host file name, which must be a valid jfs name. new volumes are 2048 blocks (1 MiB) with a 2-block root directory (32 files).
