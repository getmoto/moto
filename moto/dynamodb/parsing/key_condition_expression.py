from enum import Enum
from moto.dynamodb.exceptions import MockValidationException


class KeyConditionExpressionTokenizer:
    """
    Tokenizer for a KeyConditionExpression. Should be used as an iterator.
    The final character to be returned will be an empty string, to notify the caller that we've reached the end.
    """

    def __init__(self, expression):
        self.expression = expression
        self.token_pos = 0

    def __iter__(self):
        self.token_pos = 0
        return self

    def is_eof(self):
        return self.peek() == ""

    def peek(self):
        """
        Peek the next character without changing the position
        """
        try:
            return self.expression[self.token_pos]
        except IndexError:
            return ""

    def __next__(self):
        """
        Returns the next character, or an empty string if we've reached the end of the string.
        Calling this method again will result in a StopIterator
        """
        try:
            result = self.expression[self.token_pos]
            self.token_pos += 1
            return result
        except IndexError:
            if self.token_pos == len(self.expression):
                self.token_pos += 1
                return ""
            raise StopIteration

    def skip_characters(self, phrase, case_sensitive=False) -> None:
        """
        Skip the characters in the supplied phrase.
        If any other character is encountered instead, this will fail.
        If we've already reached the end of the iterator, this will fail.
        """
        for ch in phrase:
            if case_sensitive:
                assert self.expression[self.token_pos] == ch
            else:
                assert self.expression[self.token_pos] in [ch.lower(), ch.upper()]
            self.token_pos += 1

    def skip_white_space(self):
        """
        Skip the any whitespace characters that are coming up
        """
        try:
            while self.peek() == " ":
                self.token_pos += 1
        except IndexError:
            pass


class EXPRESSION_STAGES(Enum):
    INITIAL_STAGE = "INITIAL_STAGE"  # Can be a hash key, range key, or function
    KEY_NAME = "KEY_NAME"
    KEY_VALUE = "KEY_VALUE"
    COMPARISON = "COMPARISON"
    EOF = "EOF"


def get_key(schema, key_type):
    keys = [key for key in schema if key["KeyType"] == key_type]
    return keys[0]["AttributeName"] if keys else None


def parse_expression(
    key_condition_expression,
    expression_attribute_values,
    expression_attribute_names,
    schema,
):
    """
    Parse a KeyConditionExpression using the provided expression attribute names/values

    key_condition_expression:    hashkey = :id AND :sk = val
    expression_attribute_names:  {":sk": "sortkey"}
    expression_attribute_values: {":id": {"S": "some hash key"}}
    schema:                      [{'AttributeName': 'hashkey', 'KeyType': 'HASH'}, {"AttributeName": "sortkey", "KeyType": "RANGE"}]
    """

    current_stage: EXPRESSION_STAGES = None
    current_phrase = ""
    key_name = comparison = None
    key_values = []
    results = []
    tokenizer = KeyConditionExpressionTokenizer(key_condition_expression)
    for crnt_char in tokenizer:
        if crnt_char == " ":
            if current_stage == EXPRESSION_STAGES.INITIAL_STAGE:
                tokenizer.skip_white_space()
                if tokenizer.peek() == "(":
                    # begins_with(sk, :sk) and primary = :pk
                    #            ^
                    continue
                else:
                    # start_date < :sk and primary = :pk
                    #            ^
                    key_name = expression_attribute_names.get(
                        current_phrase, current_phrase
                    )
                    current_phrase = ""
                    current_stage = EXPRESSION_STAGES.COMPARISON
                    tokenizer.skip_white_space()
            elif current_stage == EXPRESSION_STAGES.KEY_VALUE:
                # job_id =          :id
                # job_id =          :id and  ...
                # pk=p and          x=y
                # pk=p and fn(x, y1, y1 )
                #                      ^ --> ^
                key_values.append(
                    expression_attribute_values.get(
                        current_phrase, {"S": current_phrase}
                    )
                )
                current_phrase = ""
                if comparison.upper() != "BETWEEN" or len(key_values) == 2:
                    results.append((key_name, comparison, key_values))
                    key_values = []
                tokenizer.skip_white_space()
                if tokenizer.peek() == ")":
                    tokenizer.skip_characters(")")
                    current_stage = EXPRESSION_STAGES.EOF
                    break
                elif tokenizer.is_eof():
                    break
                tokenizer.skip_characters("AND", case_sensitive=False)
                tokenizer.skip_white_space()
                if comparison.upper() == "BETWEEN":
                    # We can expect another key_value, i.e. BETWEEN x and y
                    # We should add some validation, to not allow BETWEEN x and y and z and ..
                    pass
                else:
                    current_stage = EXPRESSION_STAGES.INITIAL_STAGE
            elif current_stage == EXPRESSION_STAGES.COMPARISON:
                # hashkey = :id and sortkey       =      :sk
                # hashkey = :id and sortkey BETWEEN      x and y
                #                                  ^ --> ^
                comparison = current_phrase
                current_phrase = ""
                current_stage = EXPRESSION_STAGES.KEY_VALUE
            continue
        if crnt_char in ["=", "<", ">"] and current_stage in [
            EXPRESSION_STAGES.KEY_NAME,
            EXPRESSION_STAGES.INITIAL_STAGE,
            EXPRESSION_STAGES.COMPARISON,
        ]:
            if current_stage in [
                EXPRESSION_STAGES.KEY_NAME,
                EXPRESSION_STAGES.INITIAL_STAGE,
            ]:
                key_name = expression_attribute_names.get(
                    current_phrase, current_phrase
                )
            current_phrase = ""
            if crnt_char in ["<", ">"] and tokenizer.peek() == "=":
                comparison = crnt_char + tokenizer.__next__()
            else:
                comparison = crnt_char
            tokenizer.skip_white_space()
            current_stage = EXPRESSION_STAGES.KEY_VALUE
            continue
        if crnt_char in [","]:
            if current_stage == EXPRESSION_STAGES.KEY_NAME:
                # hashkey = :id and begins_with(sortkey,     :sk)
                #                                      ^ --> ^
                key_name = expression_attribute_names.get(
                    current_phrase, current_phrase
                )
                current_phrase = ""
                current_stage = EXPRESSION_STAGES.KEY_VALUE
                tokenizer.skip_white_space()
                continue
            else:
                raise MockValidationException(
                    f'Invalid KeyConditionExpression: Syntax error; token: "{current_phrase}"'
                )
        if crnt_char in [")"]:
            if current_stage == EXPRESSION_STAGES.KEY_VALUE:
                # hashkey = :id and begins_with(sortkey, :sk)
                #                                            ^
                value = expression_attribute_values.get(current_phrase, current_phrase)
                current_phrase = ""
                key_values.append(value)
                results.append((key_name, comparison, key_values))
                key_values = []
                tokenizer.skip_white_space()
                if tokenizer.is_eof() or tokenizer.peek() == ")":
                    break
                else:
                    tokenizer.skip_characters("AND", case_sensitive=False)
                    tokenizer.skip_white_space()
                    current_stage = EXPRESSION_STAGES.INITIAL_STAGE
                    continue
        if crnt_char in [""]:
            # hashkey =                   :id
            # hashkey = :id and sortkey = :sk
            #                                ^
            if current_stage == EXPRESSION_STAGES.KEY_VALUE:
                key_values.append(
                    expression_attribute_values.get(
                        current_phrase, {"S": current_phrase}
                    )
                )
                results.append((key_name, comparison, key_values))
                break
        if crnt_char == "(":
            # hashkey = :id and begins_with(      sortkey,     :sk)
            #                              ^ --> ^
            if current_stage in [EXPRESSION_STAGES.INITIAL_STAGE]:
                if current_phrase != "begins_with":
                    raise MockValidationException(
                        f"Invalid KeyConditionExpression: Invalid function name; function: {current_phrase}"
                    )
                comparison = current_phrase
                current_phrase = ""
                tokenizer.skip_white_space()
                current_stage = EXPRESSION_STAGES.KEY_NAME
                continue
            if current_stage is None:
                # (hash_key = :id .. )
                # ^
                continue

        current_phrase += crnt_char
        if current_stage is None:
            current_stage = EXPRESSION_STAGES.INITIAL_STAGE

    hash_value, range_comparison, range_values = validate_schema(results, schema)

    return (
        hash_value,
        range_comparison.upper() if range_comparison else None,
        range_values,
    )


# Validate that the schema-keys are encountered in our query
def validate_schema(results, schema):
    index_hash_key = get_key(schema, "HASH")
    comparison, hash_value = next(
        (
            (comparison, value[0])
            for key, comparison, value in results
            if key == index_hash_key
        ),
        (None, None),
    )
    if hash_value is None:
        raise MockValidationException(
            f"Query condition missed key schema element: {index_hash_key}"
        )
    if comparison != "=":
        raise MockValidationException("Query key condition not supported")

    index_range_key = get_key(schema, "RANGE")
    range_key, range_comparison, range_values = next(
        (
            (key, comparison, values)
            for key, comparison, values in results
            if key == index_range_key
        ),
        (None, None, []),
    )
    if index_range_key and len(results) > 1 and range_key != index_range_key:
        raise MockValidationException(
            f"Query condition missed key schema element: {index_range_key}"
        )

    return hash_value, range_comparison, range_values
