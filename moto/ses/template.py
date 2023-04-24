from typing import Any, Dict, Optional

from .exceptions import MissingRenderingAttributeException
from moto.utilities.tokenizer import GenericTokenizer


def parse_template(
    template: str,
    template_data: Dict[str, Any],
    tokenizer: Optional[GenericTokenizer] = None,
    until: Optional[str] = None,
) -> str:
    tokenizer = tokenizer or GenericTokenizer(template)
    state = ""
    parsed = ""
    var_name = ""
    for char in tokenizer:
        if until is not None and (char + tokenizer.peek(len(until) - 1)) == until:
            return parsed
        if char == "{" and tokenizer.peek() == "{":
            # Two braces next to each other indicate a variable/language construct such as for-each
            tokenizer.skip_characters("{")
            tokenizer.skip_white_space()
            if tokenizer.peek() == "#":
                state = "LOOP"
                tokenizer.skip_characters("#each")
                tokenizer.skip_white_space()
            else:
                state = "VAR"
            continue
        if char == "}":
            if state in ["LOOP", "VAR"]:
                tokenizer.skip_characters("}")
                if state == "VAR":
                    if template_data.get(var_name) is None:
                        raise MissingRenderingAttributeException(var_name)
                    parsed += template_data.get(var_name)  # type: ignore
                else:
                    current_position = tokenizer.token_pos
                    for item in template_data.get(var_name, []):
                        tokenizer.token_pos = current_position
                        parsed += parse_template(
                            template, item, tokenizer, until="{{/each}}"
                        )
                        tokenizer.skip_characters("{/each}}")
                var_name = ""
                state = ""
                continue
        if state in ["LOOP", "VAR"]:
            var_name += char
            continue
        parsed += char
    return parsed
