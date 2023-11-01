# Parsing dev documentation

Parsing happens in a structured manner and happens in different phases.
This document explains these phases.


## 1) Expression gets parsed into a tokenlist (tokenized)
A string gets parsed from left to right and gets converted into a list of tokens.
The tokens are available in `tokens.py`.

## 2) Tokenlist get transformed to expression tree (AST)
This is the parsing of the token list. This parsing will result in an Abstract Syntax Tree (AST).
The different node types are available in `ast_nodes.py`.  The AST is a representation that has all
the information that is in the expression but its tree form allows processing it in a structured manner.

## 3) The AST gets validated (full semantic correctness)
The AST is used for validation. The paths and attributes are validated to be correct. At the end of the
validation all the values will be resolved.

## 4) Update Expression gets executed using the validated AST
Finally the AST is used to execute the update expression. There should be no reason for this step to fail
since validation has completed. Due to this we have the update expressions behaving atomically (i.e. all the
actions of the update expression are performed or none of them are performed).
