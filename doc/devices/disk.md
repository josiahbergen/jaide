# filesystem

## disk controller

the disk controller allows for reading and writing to a hard disk.

### operation

the disk controller utilizes dma-style data transfer to and from a hard disk. on a read command, it copies 256 words into memory over 256 ticks (one word per tick). the device raises interrupt vector 6 on transfer complete.

### open ports

the disk controller supports communication over five ports:

| operation | port   | action              |
| --------- | ------ | ------------------- |
| write     | `0x20` | command             |
| write     | `0x21` | sector number       |
| write     | `0x22` | memory address high |
| write     | `0x23` | memory address low  |
| read      | `0x24` | status              |

### commands

there are two supported commands:

| value  | command      | action                                   |
| ------ | ------------ | ---------------------------------------- |
| `0x01` | read sector  | copies data from a sector into memory    |
| `0x02` | write sector | writes data from memory to a disk sector |

### status flags

reading from the status port returns a value with this encoding:

| bit | flag     | meaning                           |
| --- | -------- | --------------------------------- |
| 0   | idle     | device is idle                    |
| 1   | busy     | device is executing data transfer |
| 2   | error    | device error                      |

## jfs (jaide file system)

jfs is a fat-style filesystem. it uses a block size of 256 words.

the general structure of the filesystem is as follows:

| name             | size (blocks) |
| ---------------- | ------------- |
| boot             | 1             |
| allocation table | n             |
| root blocks      | m             |
| data blocks      | ...           |

### boot section

the boot section is exactly one block in length. it contains 7 values, each one word in size. all indices are word indices.

| word index | name         | description                                   |
| ---------- | ------------ | --------------------------------------------- |
| 0          | magic        | must be 0x3A33                                |
| 1          | blocks       | total number of blocks on the disk            |
| 2          | table start  | block index of the first element in the table |
| 3          | table blocks | number of blocks in the allocation table      |
| 4          | root start   | block index of the first root block           |
| 5          | root blocks  | number of blocks in the root directory        |
| 6          | data start   | block index of the first data block           |
| 7          | padding      | 249 words                                     |

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

the root directory table is 2 blocks in size. each entry is 8 words long. all indices are word indices.

the root directory can contain up to 64 files.

| word index | size (words) | name        | description                                              |
| ---------- | ------------ | ----------- | -------------------------------------------------------- |
| 0          | 4            | filename    | 8-character name, null-padded (2 chars per word)         |
| 4          | 2            | extension   | 4-character extension, null-padded                       |
| 6          | 1            | start block | first block index of the file                            |
| 7          | 1            | size        | size of the file in words                                |

#### future plan: ebnlf (executable-but-not-linkable format)

we have executable and data files

we want position-independent code. all jumps and memory references must be relative.

relative jumps is probably simple. the issue is references.
we need a basic OS that can initialize and handle interrupts for reading/writing.

we can use the stack for local variables, and that is solved

.data at the beginning, contains constants and global variables (just initialize to 0x0000)
.code segment to hold executable code
