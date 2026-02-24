# high level language ideas

basially c but slower (and with a worse compiler LOL)

if, switch statements -> compile down to labels
for loops, while loops -> also compile down to labels
pointers -> just regular vars that can be dereferenced, make sure this just maps to diff asm insts
scope -> function calls, etc. puch info to the stack (what info?)
macros, imports, header declarations -> easy enough
basic arithmatic operations -> must map directly to asm insts, operands pushed to the stack
