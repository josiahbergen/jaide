
# assembler theory
each step here should probably be its own separate file

## step 1: parse and flatten imports
- parse file with Lark
- convert tree to IR
- find imports (watch out for cycles)
- recursively repeat
- now, we will have a flat IR with macro definitions, data, and instructions

## step 2: resolve macros
- walk through IR and parse macros
- expand macros
- remove definitions when done
- now, we have just linear assembly

## step 3: resolve labels
- walk though IR and parse labels, keeping track of a simulated PC
- this will involve computing instruction sizes for the first time
- now we are ready for code generation!

## step 3: code generation
- build the actual binary string
- this will involve resolving labels, and emitting the correct bytes

## step 4: profit
🎉

# the IR

