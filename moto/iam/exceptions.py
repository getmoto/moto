from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class IAMNotFoundException(RESTError):
    code = 404

    def __init__(self, message):
        super(IAMNotFoundException, self).__init__(
            "NoSuchEntity", message)


class IAMConflictException(RESTError):
    code = 409

    def __init__(self, code='Conflict', message=""):
        super(IAMConflictException, self).__init__(
            code, message)


class IAMReportNotPresentException(RESTError):
    code = 410

    def __init__(self, message):
        super(IAMReportNotPresentException, self).__init__(
            "ReportNotPresent", message)


class MalformedCertificate(RESTError):
    code = 400

    def __init__(self, cert):
        super(MalformedCertificate, self).__init__(
            'MalformedCertificate', 'Certificate {cert} is malformed'.format(cert=cert))


class MalformedPolicyDocument(RESTError):
    code = 400

    def __init__(self, message=""):
        super(MalformedPolicyDocument, self).__init__(
            'MalformedPolicyDocument', message)


class DuplicateTags(RESTError):
    code = 400

    def __init__(self):
        super(DuplicateTags, self).__init__(
            'InvalidInput', 'Duplicate tag keys found. Please note that Tag keys are case insensitive.')


class TagKeyTooBig(RESTError):
    code = 400

    def __init__(self, tag, param='tags.X.member.key'):
        super(TagKeyTooBig, self).__init__(
            'ValidationError', "1 validation error detected: Value '{}' at '{}' failed to satisfy "
                               "constraint: Member must have length less than or equal to 128.".format(tag, param))


class TagValueTooBig(RESTError):
    code = 400

    def __init__(self, tag):
        super(TagValueTooBig, self).__init__(
            'ValidationError', "1 validation error detected: Value '{}' at 'tags.X.member.value' failed to satisfy "
                               "constraint: Member must have length less than or equal to 256.".format(tag))


class InvalidTagCharacters(RESTError):
    code = 400

    def __init__(self, tag, param='tags.X.member.key'):
        message = "1 validation error detected: Value '{}' at '{}' failed to satisfy ".format(tag, param)
        message += "constraint: Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"

        super(InvalidTagCharacters, self).__init__('ValidationError', message)


class TooManyTags(RESTError):
    code = 400

    def __init__(self, tags, param='tags'):
        super(TooManyTags, self).__init__(
            'ValidationError', "1 validation error detected: Value '{}' at '{}' failed to satisfy "
                               "constraint: Member must have length less than or equal to 50.".format(tags, param))
