

# Assembler Audit and Migration Plan

## Part 1: Audit -- Refactoring Needs

### 1.1 Global mutable state on `IRNode` (high impact)

`IRNode.labels` and `IRNode.macros` are class-level mutable dicts:

```25:27:jasm/language/ir.py
    labels: dict[str, int] = {}
    macros: dict[str, 'MacroNode'] = {}
```

This means assembling twice in the same process (e.g. for tests or a linker that processes multiple files) will carry stale state. Extract these into an `AssemblerContext` object that gets passed through the pipeline.

### 1.2 Duplicated number parsing (medium impact)

`OperandNode.get_integer_value()` (ir.py:86-98) and `DataDirectiveNode.get_number_value()` (ir.py:389-407) contain identical hex/binary/decimal parsing. Extract to a shared `parse_number(value: str, line: int) -> int` utility.

### 1.3 Duplicated constants between assembler and emulator (high impact)

[jasm/language/constants.py](jasm/language/constants.py) and [jaide/constants.py](jaide/constants.py) independently define identical opcode tables, register maps, addressing modes, and the entire `INSTRUCTION_ENCODINGS` dict. Create a shared `jaide_common/` package (or a single `isa.py` module at the project root) that both `jasm` and `jaide` import from.

### 1.4 Monolithic addressing mode resolution (high impact)

`InstructionNode.get_addressing_mode()` is a ~60-line match statement that manually maps every mnemonic to its addressing mode. With the new ISA, this becomes even harder because addressing modes are now implicit in the opcode. Refactor into a data-driven lookup: define a table of `(mnemonic, operand_pattern) -> opcode_byte` and let the lookup be automatic.

### 1.5 Repetitive `INSTRUCTION_ENCODINGS` table (medium impact)

Most ALU instructions (ADD, SUB, AND, OR, XOR, LSH, RSH, etc.) have identical encoding structures. Use a builder/factory pattern to generate these from a compact definition rather than spelling out every one individually.

### 1.6 Addressing mode set in wrong pipeline stage (medium impact)

`expand_macros()` in [jasm/macros.py](jasm/macros.py) also sets `addressing_mode` and `size` for ALL instructions, not just macro-expanded ones (lines 36-38). This is a layer violation -- addressing mode resolution should be its own explicit pipeline step between macro expansion and label resolution.

### 1.7 Parser instantiated per file (low impact)

In [jasm/parse.py](jasm/parse.py) line 64, `Lark(GRAMMAR, parser='lalr')` is called once per file. The Lark parser with `parser='lalr'` can be constructed once and reused, which would speed up multi-file assembly.

### 1.8 Fragile label mangling in macros (medium impact)

`MacroNode.expand()` only mangles label references inside `JMP|JZ|JNZ|JC|JNC` instructions (ir.py:527). It misses `CALL`, `JN`, `JNN`, `JO`, `JNO`, and any other instruction that takes a label. Should scan ALL instruction operands of type `LABELNAME`, not just specific mnemonics.

### 1.9 Expression evaluation is a no-op (low impact)

`ExpressionNode.evaluate()` always returns 0 (ir.py:459). Either implement it or remove the grammar rule so users get a clear parse error instead of silent wrong output.

---

## Part 2: Audit -- Best Practice Violations

### 2.1 `logger.fatal()` as control flow

Fatal errors call `sys.exit()` from deep within the assembler. This makes the code untestable and prevents error accumulation. Best practice: raise a custom `AssemblerError` exception, catch it at the top level. Even better, accumulate multiple errors and report them all at once.

### 2.2 No tests whatsoever

There is no test infrastructure. At minimum, add:

- Unit tests for number parsing, encoding, and label resolution
- Integration tests that assemble known `.jasm` files and compare output bytes
- A test runner in the Makefile

### 2.3 String-keyed dicts instead of enums

`OPCODES`, `ADDRESSING_MODES`, `OPERAND_TYPES` are all plain dicts. Using proper `IntEnum` types would give type safety, auto-completion, and prevent typo-based bugs.

### 2.4 Import path resolution bug

The TODO in parse.py:81 is a real bug -- different path strings pointing to the same file (e.g. relative vs absolute) bypass the circular import check. Normalize paths with `os.path.realpath()` before comparison.

### 2.5 PC tracked in words but binary in bytes

`labels.py` increments PC by `node.get_size()` which returns sizes in words, but `binary.py` produces a byte array. The implicit 2x relationship is never documented or asserted, making it easy to introduce off-by-one bugs. Make the unit explicit throughout.

---

## Part 3: Migrating Code Generation to v0.4 Spec

The new [inst.txt](doc/inst.txt) changes the encoding fundamentally:

### 3.1 Old vs New encoding format

**Old** (current assembler): opcode and addressing mode packed into one byte.

```
Byte 0: [SSSS DDDD]  (source reg, dest reg)
Byte 1: [OOOOOO MM]  (6-bit opcode << 2 | 2-bit addressing mode)
Byte 2-3: [IMM16 LE]  (optional)
```

**New** (v0.4): each instruction+mode variant gets its own full 8-bit opcode.

```
Byte 0: [SSSS DDDD]  (source reg, dest reg -- same positions)
Byte 1: [OOOOOOOO]   (full 8-bit opcode, mode implicit)
Byte 2-3: [IMM16 LE]  (optional)
```

Note: the byte order in memory is the same (reg byte first, opcode second, due to little-endian), so the `get_bytes()` emit order doesn't change.

### 3.2 What changes

**Opcode table**: Replace the current single-opcode-per-mnemonic scheme with a mapping of `(mnemonic, operand_pattern) -> opcode_byte`. The new opcodes from inst.txt:

- HALT=0x00
- GET: [reg]=0x01, [imm16+pc]=0x02, [imm16+reg]=0x03
- PUT: [reg]=0x04, [imm16+reg]=0x05
- MOV: reg=0x06, imm16=0x07
- PUSH: reg=0x08, imm16=0x09
- POP: 0x0a
- ADD: reg=0x0b, imm16=0x0c
- ADC: reg=0x0d, imm16=0x0e
- SUB: reg=0x0f, imm16=0x10
- SBC: reg=0x11, imm16=0x12 
- INC=0x13, DEC=0x14
- LSH: reg=0x15, imm16=0x16
- RSH: reg=0x17, imm16=0x18
- AND: reg=0x19, imm16=0x1a
- OR: reg=0x1b, imm16=0x1c
- NOT=0x1d (NOR is removed)
- XOR: reg=0x1e, imm16=0x1f
- INB: reg=0x20, imm16=0x21
- OUTB: reg=0x22, imm16=0x23
- CMP: reg=0x24, imm16=0x25
- JMP: reg=0x26, imm16=0x27, [imm16+pc]=0x28, [imm16+reg]=0x29
- JZ=0x2a, JNZ=0x2b, JC=0x2c, JNC=0x2d, JN=0x2e, JNN=0x2f, JO=0x30, JNO=0x31 (all PC-relative only)
- CALL: reg=0x32, imm16=0x33
- RET=0x34, INT: reg=0x35, imm16=0x36, IRET=0x37, NOP=0x38

**Instruction changes**:

- NOR removed
- JN, JNN, JO, JNO added (PC-relative only)
- GET gains [imm16+pc] mode
- PUT loses [imm16] mode, gains [imm16+reg] mode
- JMP gains direct reg and imm16 modes (non-dereferencing)
- Conditional jumps restricted to single [imm16+pc] mode
- CALL changed from address modes to direct reg/imm16

**Grammar changes needed**: The current grammar has no concept of bracket notation for memory operands. The new ISA requires syntax like `GET A, [B]`, `GET A, [0x10 + PC]`, `PUT [B + 0x10], A`. The Lark grammar needs a `memory_operand` rule:

```
memory_operand: "[" REGISTER "]"
              | "[" NUMBER "+" REGISTER "]"
              | "[" REGISTER "+" NUMBER "]"
```

**Smart label resolution for JMP/CALL**: `JMP label` should automatically emit PC-relative encoding (opcode 0x28) for intra-file labels. `JMP ABS imm16` syntax for explicit absolute jumps (opcode 0x27). The grammar needs an `ABS` keyword.

### 3.3 Concrete file changes

- **[jasm/language/constants.py](jasm/language/constants.py)**: Replace `OPCODES` with a new `OPCODE_TABLE` mapping `(mnemonic, mode) -> byte`. Remove `ADDRESSING_MODES` dict (modes are now implicit). Rewrite `INSTRUCTION_ENCODINGS`.
- **[jasm/language/grammar.py](jasm/language/grammar.py)**: Add `memory_operand` rule, `ABS` keyword, new mnemonics (ADDC, SUBC, JN, JNN, JO, JNO), remove NOR.
- **[jasm/language/ir.py](jasm/language/ir.py)**: Rewrite `InstructionNode.get_addressing_mode()`, `get_bytes()`, and `validate_instruction_semantics()`. The `get_bytes()` method no longer needs to pack opcode+mode; it just emits the opcode byte directly.
- **[jasm/parse.py](jasm/parse.py)**: Handle new `memory_operand` parse tree nodes, producing operand nodes that carry bracket/offset information.
- **[jaide/constants.py](jaide/constants.py)**: Mirror all opcode changes for the emulator (or share a common module).
- **[jaide/emulator.py](jaide/emulator.py)**: Update the instruction decoder to use 8-bit opcodes directly.

---

## Part 4: Adding a Linker

### 4.1 Object file format

Define a simple `.jo` (jaide object) format:

```
HEADER (fixed size)
  magic:          0x4A4F  ("JO")
  version:        u16
  code_size:      u16     (words)
  sym_count:      u16
  reloc_count:    u16

CODE SEGMENT
  raw machine code with 0x0000 placeholders for unresolved references

SYMBOL TABLE (sym_count entries)
  name_length:    u8
  name:           [u8; name_length]
  offset:         u16     (word offset within this object)
  flags:          u8      (LOCAL=0, GLOBAL=1, EXTERN=2)

RELOCATION TABLE (reloc_count entries)
  offset:         u16     (word offset of the placeholder in code)
  symbol_index:   u16     (index into symbol table)
  type:           u8      (ABS=0, PC_REL=1)
```

### 4.2 Assembler changes for linkable output

- Add `EXPORT label` and `EXTERN label` directives to the grammar and parser
- When assembling with `-c` (compile-only) flag, output `.jo` object files instead of raw binaries
- For intra-file label references, compute PC-relative offsets at assembly time (no relocation needed)
- For `EXTERN` symbols, emit a placeholder and add a relocation entry
- For `EXPORT` symbols, add them to the symbol table with GLOBAL flag
- All other labels are LOCAL (resolved within the file, not visible to linker)

### 4.3 Linker implementation (`jlink/`)

Create a new `jlink` package:

- `jlink/__main__.py` -- CLI entry point: `python -m jlink file_a.jo file_b.jo -o program.bin`
- `jlink/object_file.py` -- Parse `.jo` files, expose code/symbols/relocations
- `jlink/linker.py` -- Core logic:
  1. Read all input object files
  2. Layout: concatenate code segments, assign base addresses (first file at 0x0000 or user-specified origin via `-b` flag)
  3. Build global symbol table from all files
  4. Resolve: for each relocation entry, look up the symbol, compute the final address, patch the code
  5. Emit final raw binary

### 4.4 Smart `JMP label` behavior

The assembler should automatically pick the right encoding:

- `JMP label` where `label` is defined in the same file: emit `JMP [imm16+pc]` (opcode 0x28), compute offset at assembly time, no relocation needed
- `JMP label` where `label` is declared `EXTERN`: emit `JMP imm16` (opcode 0x27) with placeholder, add ABS relocation entry
- `JMP ABS 0x0200`: always emit `JMP imm16` (opcode 0x27) with literal value, no relocation

Same logic applies to `CALL`, and conditionals always use PC-relative.

### 4.5 Build flow

```
jasm file_a.jasm -c -o file_a.jo    # assemble to object
jasm file_b.jasm -c -o file_b.jo    # assemble to object
jlink file_a.jo file_b.jo -o program.bin  # link to binary
jasm file_a.jasm -o program.bin      # single-file shortcut (no linker needed)
```

---

## Recommended Execution Order

The work naturally phases as follows, with each phase building on the previous:

1. **Refactor foundations** -- Extract shared state, deduplicate code, fix bugs (Part 1)
2. **Migrate to v0.4 encoding** -- New opcode table, grammar changes, encoding rewrite (Part 3)
3. **Update emulator** -- Match the new opcodes in the emulator decoder
4. **Add linker infrastructure** -- Object file format, assembler `-c` mode, `EXPORT`/`EXTERN` directives (Part 4)
5. **Implement linker** -- `jlink` package (Part 4)
6. **Add tests** -- Now that the architecture is stable (Part 2.2)

