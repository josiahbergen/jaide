# filesystem

## jfs (jaide file system)

jfs is a fat-style filesystem. it uses a block size of 256 words (512 bytes).

the general structure of the filesystem is as follows:

| name             | size (blocks) |
| ---------------- | ------------- |
| boot             | 1             |
| allocation table | N             |
| root blocks      | M             |
| data blocks      | ...           |

### boot section

the boot section is exactly one block in length. it contains 6 values, each of them being one word in size:

| index | name         | description                                   |
| ----- | ------------ | --------------------------------------------- |
| 0     | magic        | must be 0x3A33                                |
| 1     | blocks       | total number of blocks on the disk            |
| 2     | table start  | block index of the first element in the table |
| 3     | table blocks | number of blocks in the allocation table      |
| 4     | root start   | block index of the first root block           |
| 5     | root blocks  | number of blocks in the root directory        |
| 6     | data start   | block index of the first data block           |
| 7     | padding      | 498 bytes in size                             |

### allocation table

each entry in the allocation table is one word (16 bits) in size.

with a few exceptions, the value of the entry is simply the index of the next block.

special values:

| value    | meaning      |
| -------- | ------------ |
| `0x0000` | unallocated  |
| `0xffff` | end of chain |

indexing: table entry indexing uses absolute block numbers.

### root directory table

the root directory table is 2 blocks in size. each entry is 16 bytes in size.

the root directory can contain up to 64 files.

| byte index | size (bytes) | name        | description                         |
| ---------- | ------------ | ----------- | ----------------------------------- |
| 0          | 8            | filename    | the name of the file, space padded. |
| 8          | 3            | extension   | the file's extension.               |
| 11         | 1            | flags       | unused, set to 0x00                 |
| 12         | 2            | start block | first block index of the file       |
| 14         | 2            | size        | size of the file in bytes           |

## ebnlf (executable-but-not-linkable format)

we have executable and data files

we want position-independent code. all jumps and memory references must be relative.

relative jumps is probably simple. the issue is references.
we need a basic OS that can initialize and handle interrupts for reading/writing.

we can use the stack for local variables, and that is solved

.data at the beginning, contains constants and global variables (just initialize to 0x0000)
.code segment to hold executable code

gotta implement signed types

| offset | size (words) | description            |
| ------ | ------------ | ---------------------- |
| 0      | 1            | magic (must be 0x3A33) |
| 2      | 2            | size of                |
