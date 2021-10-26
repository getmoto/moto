from moto.dynamodb2.limits import HASH_KEY_MAX_LENGTH, RANGE_KEY_MAX_LENGTH


class InvalidIndexNameError(ValueError):
    pass


class MockValidationException(ValueError):
    def __init__(self, message):
        self.exception_msg = message


class InvalidUpdateExpressionInvalidDocumentPath(MockValidationException):
    invalid_update_expression_msg = (
        "The document path provided in the update expression is invalid for update"
    )

    def __init__(self):
        super(InvalidUpdateExpressionInvalidDocumentPath, self).__init__(
            self.invalid_update_expression_msg
        )


class InvalidUpdateExpression(MockValidationException):
    invalid_update_expr_msg = "Invalid UpdateExpression: {update_expression_error}"

    def __init__(self, update_expression_error):
        self.update_expression_error = update_expression_error
        super(InvalidUpdateExpression, self).__init__(
            self.invalid_update_expr_msg.format(
                update_expression_error=update_expression_error
            )
        )


class AttributeDoesNotExist(MockValidationException):
    attr_does_not_exist_msg = (
        "The provided expression refers to an attribute that does not exist in the item"
    )

    def __init__(self):
        super(AttributeDoesNotExist, self).__init__(self.attr_does_not_exist_msg)


class ProvidedKeyDoesNotExist(MockValidationException):
    provided_key_does_not_exist_msg = (
        "The provided key element does not match the schema"
    )

    def __init__(self):
        super(ProvidedKeyDoesNotExist, self).__init__(
            self.provided_key_does_not_exist_msg
        )


class ExpressionAttributeNameNotDefined(InvalidUpdateExpression):
    name_not_defined_msg = "An expression attribute name used in the document path is not defined; attribute name: {n}"

    def __init__(self, attribute_name):
        self.not_defined_attribute_name = attribute_name
        super(ExpressionAttributeNameNotDefined, self).__init__(
            self.name_not_defined_msg.format(n=attribute_name)
        )


class AttributeIsReservedKeyword(InvalidUpdateExpression):
    attribute_is_keyword_msg = (
        "Attribute name is a reserved keyword; reserved keyword: {keyword}"
    )

    def __init__(self, keyword):
        self.keyword = keyword
        super(AttributeIsReservedKeyword, self).__init__(
            self.attribute_is_keyword_msg.format(keyword=keyword)
        )


class ExpressionAttributeValueNotDefined(InvalidUpdateExpression):
    attr_value_not_defined_msg = "An expression attribute value used in expression is not defined; attribute value: {attribute_value}"

    def __init__(self, attribute_value):
        self.attribute_value = attribute_value
        super(ExpressionAttributeValueNotDefined, self).__init__(
            self.attr_value_not_defined_msg.format(attribute_value=attribute_value)
        )


class UpdateExprSyntaxError(InvalidUpdateExpression):
    update_expr_syntax_error_msg = "Syntax error; {error_detail}"

    def __init__(self, error_detail):
        self.error_detail = error_detail
        super(UpdateExprSyntaxError, self).__init__(
            self.update_expr_syntax_error_msg.format(error_detail=error_detail)
        )


class InvalidTokenException(UpdateExprSyntaxError):
    token_detail_msg = 'token: "{token}", near: "{near}"'

    def __init__(self, token, near):
        self.token = token
        self.near = near
        super(InvalidTokenException, self).__init__(
            self.token_detail_msg.format(token=token, near=near)
        )


class InvalidExpressionAttributeNameKey(MockValidationException):
    invalid_expr_attr_name_msg = (
        'ExpressionAttributeNames contains invalid key: Syntax error; key: "{key}"'
    )

    def __init__(self, key):
        self.key = key
        super(InvalidExpressionAttributeNameKey, self).__init__(
            self.invalid_expr_attr_name_msg.format(key=key)
        )


class ItemSizeTooLarge(MockValidationException):
    item_size_too_large_msg = "Item size has exceeded the maximum allowed size"

    def __init__(self):
        super(ItemSizeTooLarge, self).__init__(self.item_size_too_large_msg)


class ItemSizeToUpdateTooLarge(MockValidationException):
    item_size_to_update_too_large_msg = (
        "Item size to update has exceeded the maximum allowed size"
    )

    def __init__(self):
        super(ItemSizeToUpdateTooLarge, self).__init__(
            self.item_size_to_update_too_large_msg
        )


class HashKeyTooLong(MockValidationException):
    # deliberately no space between of and {lim}
    key_too_large_msg = "One or more parameter values were invalid: Size of hashkey has exceeded the maximum size limit of{lim} bytes".format(
        lim=HASH_KEY_MAX_LENGTH
    )

    def __init__(self):
        super(HashKeyTooLong, self).__init__(self.key_too_large_msg)


class RangeKeyTooLong(MockValidationException):
    key_too_large_msg = "One or more parameter values were invalid: Aggregated size of all range keys has exceeded the size limit of {lim} bytes".format(
        lim=RANGE_KEY_MAX_LENGTH
    )

    def __init__(self):
        super(RangeKeyTooLong, self).__init__(self.key_too_large_msg)


class IncorrectOperandType(InvalidUpdateExpression):
    inv_operand_msg = "Incorrect operand type for operator or function; operator or function: {f}, operand type: {t}"

    def __init__(self, operator_or_function, operand_type):
        self.operator_or_function = operator_or_function
        self.operand_type = operand_type
        super(IncorrectOperandType, self).__init__(
            self.inv_operand_msg.format(f=operator_or_function, t=operand_type)
        )


class IncorrectDataType(MockValidationException):
    inc_data_type_msg = "An operand in the update expression has an incorrect data type"

    def __init__(self):
        super(IncorrectDataType, self).__init__(self.inc_data_type_msg)


class ConditionalCheckFailed(ValueError):
    msg = "The conditional request failed"

    def __init__(self):
        super(ConditionalCheckFailed, self).__init__(self.msg)


class TransactionCanceledException(ValueError):
    cancel_reason_msg = "Transaction cancelled, please refer cancellation reasons for specific reasons [{}]"

    def __init__(self, errors):
        msg = self.cancel_reason_msg.format(", ".join([str(err) for err in errors]))
        super(TransactionCanceledException, self).__init__(msg)


class EmptyKeyAttributeException(MockValidationException):
    empty_str_msg = "One or more parameter values were invalid: An AttributeValue may not contain an empty string"
    # AWS has a different message for empty index keys
    empty_index_msg = "One or more parameter values are not valid. The update expression attempted to update a secondary index key to a value that is not supported. The AttributeValue for a key attribute cannot contain an empty string value."

    def __init__(self, key_in_index=False):
        super(EmptyKeyAttributeException, self).__init__(
            self.empty_index_msg if key_in_index else self.empty_str_msg
        )


class UpdateHashRangeKeyException(MockValidationException):
    msg = "One or more parameter values were invalid: Cannot update attribute {}. This attribute is part of the key"

    def __init__(self, key_name):
        super(UpdateHashRangeKeyException, self).__init__(self.msg.format(key_name))


class TooManyAddClauses(InvalidUpdateExpression):
    msg = 'The "ADD" section can only be used once in an update expression;'

    def __init__(self):
        super(TooManyAddClauses, self).__init__(self.msg)
