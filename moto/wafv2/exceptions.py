from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class WAFv2ClientError(RESTError):
    code = 400


class WAFV2DuplicateItemException(WAFv2ClientError):
    def __init__(self):
        super(WAFV2DuplicateItemException, self).__init__(
            "WafV2DuplicateItem",
            "AWS WAF could not perform the operation because some resource in your request is a duplicate of an existing one.",
        )


class WAFNonexistentItemException(WAFv2ClientError):
    def __init__(self):
        super(WAFNonexistentItemException, self).__init__(
            "WAFNonexistentItem",
            "AWS WAF could not perform the operation because your resource does not exist.",
        )
