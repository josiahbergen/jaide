# jaideos kernel abi (syscall interface)

the jaideos kernel supports a low-level interface of syscalls, mostly for system + driver functionality.

## interface

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

### tilesystem

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

### other devices

| #      | Name        | Args | Returns                      | Notes                                                          |
| ------ | ----------- | ---- | ---------------------------- | -------------------------------------------------------------- |
| `0x40` | `get_ticks` |      | A = low word, B = high word  | 32-bit kernel tick counter, incremented by PIT ISR (vector 5). |
| `0x41` | `get_date`  |      | A = year, B = month, C = day | Read RTC (ports `0x30–0x33`).                                  |
| `0x41` | `get_time`  |      | A = hours, B = minutes,      | Read RTC (ports `0x30–0x33`).                                  |

### system

| #      | Name       | Args | Returns | Notes           |
| ------ | ---------- | ---- | ------- | --------------- |
| `0x50` | `reset`    | -    | -       | Reset system    |
| `0x51` | `shutdown` | -    | -       | Shutdown system |
