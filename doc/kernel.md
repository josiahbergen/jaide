# jaideos kernel

the jaideos kernel is pretty cool. read all about it below!

## syscall interface

the kernel supports a low-level interface of syscalls, mostly for system + driver functionality.

syscalls can be invoked via a software interrupt with `int 0x10`.

### arguments

| register      | use                          |
| ------------- | ---------------------------- |
| `a`           | syscall number               |
| `b`, `c`, `d` | other arguments (as defined) |

### return values

| register      | use                               |
| ------------- | --------------------------------- |
| `a`           | zero on success, nonzero on error |
| `b`, `c`, `d` | as defined                        |

### register usage

| caller-saved (clobbered) | callee-saved (preserved)       |
| ------------------------ | ------------------------------ |
| `a`, `b`, `c`, `d`, `f`  | `e`, `x`, `y`, `z`, `sp`, `mb` |

## syscall table

### process

| #      | Name   | Args          | Returns                              | Notes                                                |
| ------ | ------ | ------------- | ------------------------------------ | ---------------------------------------------------- |
| `0x00` | `exit` | B = exit code |                                      | Return to shell. No-op if called from shell context. |
| `0x01` | `exec` | B = string    | A = error (never returns on success) | Load and execute file from disk.                     |

### terminal output

| #      | Name          | Args                   | Returns      | Notes                                                                    |
| ------ | ------------- | ---------------------- | ------------ | ------------------------------------------------------------------------ |
| `0x10` | `write_str`   | B = string             | -            | Print string at cursor. Scrolls.                                         |
| `0x11` | `write_char`  | B = char               | -            | Print one character. Advances cursor. Scrolls at EOL.                    |
| `0x12` | `clear`       | -                      | -            | Blank VRAM, reset cursor to (0, 0).                                      |
| `0x13` | `set_cursor`  | B = x, C = y           | -            | Move kernel cursor. x: 0–79, y: 0–24.                                    |
| `0x14` | `get_cursor`  | -                      | B = x, C = y | Read current cursor position.                                            |
| `0x15` | `put_char_at` | B = char, C = x, D = y | -            | Write one glyph directly to VRAM. No cursor update, no scroll.           |
| `0x16` | `set_col`     | B = attr               | -            | Set color attribute for subsequent `write_*` calls. Default is `0x0001`. |

### terminal input

| #      | Name        | Args                  | Returns                            | Notes                                                          |
| ------ | ----------- | --------------------- | ---------------------------------- | -------------------------------------------------------------- |
| `0x20` | `read_char` | -                     | A = char                           | **Blocking.** Returns raw key code.                            |
| `0x21` | `poll_key`  | -                     | A = char or 0                      | **Non-blocking.** Returns next key from buffer, or 0 if empty. |
| `0x22` | `read_line` | B = buff, C = max len | A = len (includes null terminator) | Collect input with echo and backspace until ENTER.             |

### filesystem

| #      | Name       | Args                               | Returns                               | Notes                                                                 |
| ------ | ---------- | ---------------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| `0x30` | `fs_mount` | -                                  | A = status                            | Read boot sector, validate magic, cache header values.                |
| `0x31` | `fs_list`  | B = buff, C = max entries          | A = count                             | Copy root directory entries into buffer.                              |
| `0x32` | `fs_open`  | B = filename                       | A = fd                                | Walk root dir, return index into kernel FD table. Error if not found. |
| `0x33` | `fs_read`  | B = fd, C = dest addr, D = n_words | A = words read                        | Read words from current file position, following FAT chain.           |
| `0x34` | `fs_write` | B = fd, C = src addr, D = n_words  | A = status                            | Write words at current file position. Allocates new blocks as needed. |
| `0x35` | `fs_seek`  | B = fd, C = word offset            | A = status                            | Move read/write position within file.                                 |
| `0x36` | `fs_close` | B = fd                             | -                                     | Release FD table slot. Flush any pending writes.                      |
| `0x37` | `fs_stat`  | B = filename                       | A = status, B = start block, C = size | Query file metadata without opening.                                  |

### time

| #      | Name        | Args | Returns                      | Notes                                                          |
| ------ | ----------- | ---- | ---------------------------- | -------------------------------------------------------------- |
| `0x40` | `get_ticks` |      | A = low word, B = high word  | 32-bit kernel tick counter, incremented by PIT ISR (vector 5). |
| `0x41` | `get_date`  |      | A = year, B = month, C = day | Read RTC (MMIO `0xFE30–0xFE33`).                               |
| `0x41` | `get_time`  |      | A = hours, B = minutes,      | Read RTC (MMIO `0xFE30–0xFE33`).                               |

### system

| #      | Name       | Args | Returns | Notes           |
| ------ | ---------- | ---- | ------- | --------------- |
| `0x50` | `reset`    | -    | -       | Reset system    |
| `0x51` | `shutdown` | -    | -       | Shutdown system |

## memory layout

the jaide kernel requires a specific memory layout:

| range             | purpose                                      |
| ----------------- | -------------------------------------------- |
| `0x0000`–`0x00FF` | bios rom                                     |
| `0x0100`–`0x3FFF` | kernel code                                  |
| `0x4000`–`0x4FFF` | video memory                                 |
| `0x5000`–`0x5FFF` | kernel data                                  |
| `0x6000`–`0x6FFF` | filesystem block cache                       |
| `0x7000`–`0xAFFF` | user program space (banked)                  |
| `0xB000`–`0xFCFF` | reserved                                     |
| `0xFD00`–`0xFDFF` | stack                                        |
| `0xFE00`–`0xFEFF` | mmio                                         |
| `0xFF00`–`0xFFFF` | interrupt vector table                       |

### kernel data layout

| range             | size (words) | purpose                  |
| ----------------- | ------------ | ------------------------ |
| `0x5200...0x5FFF` | 0xE00        | reserved/scratch         |
| `0x51C0...0x51FF` | 0x40         | shell variables          |
| `0x5180...0x51BF` | 0x40         | filesystem cache indices |
| `0x5140...0x517F` | 0x40         | file descriptor table*   |
| `0x5100...0x513F` | 0x40         | kernel variables**       |
| `0x5000...0x50FF` | 0x100        | disk scratch buffer      |

#### file descriptor table

the file descriptor table is a 64-word array of eight 8-word file descriptor structs:

| word index | name           |
| ---------- | -------------- |
| 0          | open           |
| 1          | start block    |
| 2          | current block  |
| 3          | current offset |
| 4          | size           |
| 5-7        | padding        |

#### kernel variables

the kernel variable section contains these defined values:

| address    | name         | description                                   |
| ---------- | ------------ | --------------------------------------------- |
| 0x5100     | pit low      | low word of 32-bit kernel PIT counter         |
| 0x5101     | pit high     | high word of 32-bit kernel PIT counter        |
| 0x5102     | fs mounted   | 0x01 if filesystem mounted, 0x00 otherwise    |
| 0x5103     | blocks       | total number of blocks on the disk            |
| 0x5104     | table start  | block index of the first element in the table |
| 0x5105     | table blocks | number of blocks in the allocation table      |
| 0x5106     | root start   | block index of the first root block           |
| 0x5107     | root blocks  | number of blocks in the root directory        |
| 0x5108     | data start   | block index of the first data block           |
| 0x5109     | padding      | 54 words                                      |

### user programs

programs loaded by `exec` are placed at **`0x7000`** in their assigned memory bank (`MB = 1`–`31`). the entry point is **`0x7000`**. each bank provides 16,384 words (32 KiB) for code and data.
