class MessageNotInflight(Exception):
    description = "The message referred to is not in flight."
    status_code = 400


class ReceiptHandleIsInvalid(Exception):
    description = "The receipt handle provided is not valid."
    status_code = 400
