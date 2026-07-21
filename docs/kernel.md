# kernel

the kernel is pretty cool. read all about it below!

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

| caller-saved (clobbered)                           | callee-saved (preserved)       |
| -------------------------------------------------- | ------------------------------ |
| `a`, `b`, `c`, `d`, `f`, `e`, `x`, `y`, `z`, `sp`  | `mb`                           |


## kernel tty

`kernel/src/tty.jasm` contains the underlying logic behind all text-mode graphics. 

the terminal output syscalls in `kernel/syscalls/output.jasm` are thin wrappers over the interface defined by `tty.jasm`. kernel code (such as the built-in shell) calls this module directly. 

## syscall table

### process

| #      | name   | args          | returns                              | notes                                                |
| ------ | ------ | ------------- | ------------------------------------ | ---------------------------------------------------- |
| `0x00` | `exit` | b = exit code |                                      | return to shell. no-op if called from shell context. |
| `0x01` | `exec` | b = string    | a = error (never returns on success) | load and execute file from disk.                     |

### terminal output

| #      | name          | args                   | returns      | notes                                                                    |
| ------ | ------------- | ---------------------- | ------------ | ------------------------------------------------------------------------ |
| `0x10` | `write_str`   | b = string             | -            | print string at cursor. scrolls.                                         |
| `0x11` | `write_char`  | b = char               | -            | print one character. advances cursor, scrolls.                           |
| `0x12` | `clear`       | -                      | -            | blank vram, reset cursor to (0, 0).                                      |
| `0x13` | `set_cursor`  | b = x, c = y           | -            | move kernel cursor. x: 0–79, y: 0–24.                                    |
| `0x14` | `get_cursor`  | -                      | b = x, c = y | read current cursor position.                                            |
| `0x15` | `put_char_at` | b = char, c = x, d = y | -            | write one glyph directly to vram. no cursor update, no scroll.           |
| `0x16` | `set_attr`    | b = attr               | -            | set color attribute for subsequent `write_*` calls. default is `0x0001`. |

### terminal input

| #      | name        | args                  | returns                            | notes                                                          |
| ------ | ----------- | --------------------- | ---------------------------------- | -------------------------------------------------------------- |
| `0x20` | `read_char` | -                     | a = char                           | **blocking!** returns raw key code.                            |
| `0x21` | `poll_key`  | -                     | a = char or 0                      | non-blocking. returns next key from buffer, or 0 if empty. |
| `0x22` | `read_line` | b = buff, c = max len | a = len (includes null terminator) | collect input with echo and backspace until enter.             |

### filesystem

| #      | name       | args                               | returns                               | notes                                                                 |
| ------ | ---------- | ---------------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| `0x30` | `fs_mount` | -                                  | a = status                            | read boot sector, validate magic, cache header values.                |
| `0x31` | `fs_list`  | b = buff, c = max entries          | a = count                             | copy root directory entries into buffer.                              |
| `0x32` | `fs_open`  | b = filename                       | a = fd                                | walk root dir, return index into kernel fd table. error if not found. |
| `0x33` | `fs_read`  | b = fd, c = dest addr, d = n_words | a = words read                        | read words from current file position, following fat chain.           |
| `0x34` | `fs_write` | b = fd, c = src addr, d = n_words  | a = status                            | write words at current file position. allocates new blocks as needed. |
| `0x35` | `fs_seek`  | b = fd, c = word offset            | a = status                            | move read/write position within file.                                 |
| `0x36` | `fs_close` | b = fd                             | -                                     | release fd table slot. flush any pending writes.                      |
| `0x37` | `fs_stat`  | b = filename                       | a = status, b = start block, c = size | query file metadata without opening.                                  |

### time

| #      | name        | args | returns                      | notes                                                          |
| ------ | ----------- | ---- | ---------------------------- | -------------------------------------------------------------- |
| `0x40` | `get_ticks` |      | a = low word, b = high word  | 32-bit kernel tick counter, incremented by pit isr (vector 5). |
| `0x41` | `get_date`  |      | a = year, b = month, c = day | read rtc (mmio `0xfe30–0xfe33`).                               |
| `0x41` | `get_time`  |      | a = hours, b = minutes,      | read rtc (mmio `0xfe30–0xfe33`).                               |

### system

| #      | name       | args | returns | notes           |
| ------ | ---------- | ---- | ------- | --------------- |
| `0x50` | `reset`    | -    | -       | reset system    |
| `0x51` | `shutdown` | -    | -       | shutdown system |

## memory layout

the jaide kernel requires a specific memory layout:

| range             | purpose                                      |
| ----------------- | -------------------------------------------- |
| `0x0000`–`0x00ff` | bios rom                                     |
| `0x0100`–`0x3fff` | kernel code                                  |
| `0x4000`–`0x4fff` | video memory                                 |
| `0x5000`–`0x5fff` | kernel data                                  |
| `0x6000`–`0x6fff` | filesystem block cache                       |
| `0x7000`–`0xafff` | user program space (banked)                  |
| `0xb000`–`0xfcff` | reserved                                     |
| `0xfd00`–`0xfdff` | stack                                        |
| `0xfe00`–`0xfeff` | mmio                                         |
| `0xff00`–`0xffff` | interrupt vector table                       |

### kernel data layout

| range             | size (words) | purpose                  |
| ----------------- | ------------ | ------------------------ |
| `0x5200...0x5fff` | 0xe00        | reserved/scratch         |
| `0x51c0...0x51ff` | 0x40         | shell variables          |
| `0x5180...0x51bf` | 0x40         | filesystem cache indices |
| `0x5140...0x517f` | 0x40         | file descriptor table*   |
| `0x5100...0x513f` | 0x40         | kernel variables**       |
| `0x5000...0x50ff` | 0x100        | disk scratch buffer      |

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
| 0x5100     | pit low      | low word of 32-bit kernel pit counter         |
| 0x5101     | pit high     | high word of 32-bit kernel pit counter        |
| 0x5102     | fs mounted   | 0x01 if filesystem mounted, 0x00 otherwise    |
| 0x5103     | blocks       | total number of blocks on the disk            |
| 0x5104     | table start  | block index of the first element in the table |
| 0x5105     | table blocks | number of blocks in the allocation table      |
| 0x5106     | root start   | block index of the first root block           |
| 0x5107     | root blocks  | number of blocks in the root directory        |
| 0x5108     | data start   | block index of the first data block           |
| 0x5109     | cursor row   | tty cursor row, 0-24                           |
| 0x510a     | cursor col   | tty cursor column, 0-79                        |
| 0x510b     | tty attr     | attribute used for subsequent tty writes      |
| 0x510c     | padding      | 52 words                                       |

### user programs

programs loaded by `exec` are placed at **`0x7000`** in their assigned memory bank (`mb = 1`–`31`). the entry point is **`0x7000`**. each bank provides 16,384 words (32 kib) for code and data.
