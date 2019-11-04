class InvalidIndexNameError(ValueError):
    pass


class InvalidUpdateExpression(ValueError):
    pass


class ItemSizeTooLarge(Exception):
    message = "Item size has exceeded the maximum allowed size"
