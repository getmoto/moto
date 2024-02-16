from typing import List

from moto.core.exceptions import JsonRESTError


class DomainLimitExceededException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__('DomainLimitExceeded', 'The number of domains has exceeded the allowed threshold for the account.')


class DuplicateRequestException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__('DuplicateRequest', 'The request is already in progress for the domain.')


class InvalidInputException(JsonRESTError):
    code = 400

    def __init__(self, error_msgs: List[str]):
        error_msgs_str = '\n\t'.join(error_msgs)
        super().__init__('InvalidInput', f'The requested item is not acceptable.\n\t{error_msgs_str}')


class OperationLimitExceededException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__('OperationLimitExceeded', 'The top-level domain does not support this operation.')


class UnsupportedTLDException(JsonRESTError):
    code = 400

    def __init__(self, tld: str):
        super().__init__('UnsupportedTLD', f'Amazon Route53 does not support the top-level domain (TLD) `.{tld}`.')