from moto.core.exceptions import RESTError


class WAFv2ClientError(RESTError):
    code = 400


class WAFV2DuplicateItemException(WAFv2ClientError):
    def __init__(self):
        super(WAFV2DuplicateItemException, self).__init__(
            "WafV2DuplicateItem",
            "AWS WAF could not perform the operation because some resource in your request is a duplicate of an existing one.",
        )
