class InvalidIndexNameError(ValueError):
    pass


class MockValidationException(ValueError):
    def __init__(self, message):
        self.exception_msg = message


class InvalidUpdateExpression(MockValidationException):
    invalid_update_expression_msg = (
        "The document path provided in the update expression is invalid for update"
    )

    def __init__(self):
        super(InvalidUpdateExpression, self).__init__(
            self.invalid_update_expression_msg
        )


class UpdateExprSyntaxError(MockValidationException):
    update_expr_syntax_error_msg = (
        "Invalid UpdateExpression: Syntax error; {error_detail}"
    )

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
