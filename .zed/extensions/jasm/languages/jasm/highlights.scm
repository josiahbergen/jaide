(comment) @comment
(string) @string
(escape_sequence) @escape

(directive) @keyword
(macro_keyword) @keyword
(mnemonic) @function
(register) @variable.special
(label_definition name: (identifier) @type)
(label_reference) @variable
(macro_argument name: (identifier) @variable.parameter)

(number) @number
(operator) @operator
"," @punctuation.delimiter
":" @punctuation.delimiter
"[" @punctuation.bracket
"]" @punctuation.bracket
"(" @punctuation.bracket
")" @punctuation.bracket
