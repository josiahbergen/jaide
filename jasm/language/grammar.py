# language/grammar.py
# grammar definition for the JASM language.
# josiah bergen, december 2025

GRAMMAR = r"""
    start: (_NL | statement)*
    
    ?statement: instruction
                | directive
                | macro_definition
                | macro_call
                | label

    # Directives 
    directive: data_directive | import_directive

    data_directive: DATA constant ("," constant)*
    import_directive: IMPORT STRING

    # Macros 
    # Matches: MACRO name args \n body END MACRO
    macro_definition: MACRO LABELNAME macro_definition_args? _NL macro_body END MACRO

    macro_definition_args: macro_arg ("," macro_arg)*
    
    # A macro body contains lines, but valid lines inside a macro are restricted 
    # (instructions, data, or nested calls)
    macro_body: (_NL | macro_stmt)*
    
    ?macro_stmt: instruction
               | data_directive
               | macro_call

    # Macro call: name [args]
    macro_call: LABELNAME operand_list?

    # Instructions 
    instruction: MNEMONIC operand_list?
    operand_list: generic_operand ("," generic_operand)*

    # Operands & Expressions 
    ?generic_operand: operand
               | macro_arg
               | expression

    ?operand: register_pair
            | REGISTER
            | NUMBER
            | LABELNAME

    macro_arg: "%" LABELNAME

    # EBNF: expression = "(" [ operator ] exp_term { operator exp_term } ")"
    # We allow an optional leading operator for unary contexts (e.g. (- 5))
    expression: "(" OPERATOR? exp_term (OPERATOR exp_term)* ")"

    ?exp_term: NUMBER
             | macro_arg
             | expression

    # Register pair rule (allows whitespace, e.g., "A : B")
    register_pair: REGISTER ":" REGISTER

    label: LABELNAME ":"

    ?constant: NUMBER | STRING

    # Terminals & Lexer 

    # Operators
    OPERATOR: "+" | "-" | "*" | "/" | "%" | "<<" | ">>" | "&" | "|" | "^" | "~"

    # Mnemonics
    # Priority 100 ensures these are matched before generic LABELNAMEs
    MNEMONIC.100: /(GET|PUT|MOV|PUSH|POP|ADD|ADC|SUB|SBC|INC|DEC|LSH|RSH|AND|OR|NOR|NOT|XOR|INB|OUTB|CMP|JMP|JZ|JNZ|JC|JNC|CALL|RET|INT|IRET|HALT|NOP)\b/i

    # Directives (priority 95 ensures these are matched before LABELNAME)
    DATA.95: /DATA\b/i
    IMPORT.95: /IMPORT\b/i
    
    # Macro keywords (priority 95 ensures these are matched before LABELNAME)
    MACRO.95: /MACRO\b/i
    END.95: /END\b/i

    # Registers
    # Priority 90 ensures 'A' is parsed as a Register, not a Label
    REGISTER.90: /(A|B|C|D|E|X|Y|SP|PC|Z|F|MB)\b/i

    # Numbers
    # Hex (0x...), Bin (b...), Dec (0-9...)
    # Priority 20 ensures numbers are matched before LABELNAME (priority 10)
    NUMBER.20: /0x[0-9a-fA-F]+/
          | /b[01]+/
          | /[0-9]+/

    # Strings (Double quoted)
    STRING: /"[^"]*"/

    # Identifiers (Labels, Macro names)
    # Priority 10 is lower than Keywords/Registers
    LABELNAME.10: /[A-Za-z_][A-Za-z0-9_]*/

    # Comments (semicolon to end of line)
    COMMENT: /;.*/

    # Whitespace Handling
    # We distinguish between Newlines (structural) and Inline Whitespace (ignored)
    _NL: /(\r?\n)+/
    WS_INLINE: /[ \t]+/

    %ignore WS_INLINE
    %ignore COMMENT
"""
