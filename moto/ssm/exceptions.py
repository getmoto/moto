from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class InvalidFilterKey(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidFilterKey, self).__init__("InvalidFilterKey", message)


class InvalidFilterOption(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidFilterOption, self).__init__("InvalidFilterOption", message)


class InvalidFilterValue(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidFilterValue, self).__init__("InvalidFilterValue", message)


class ParameterNotFound(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ParameterNotFound, self).__init__("ParameterNotFound", message)


class ParameterVersionNotFound(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ParameterVersionNotFound, self).__init__(
            "ParameterVersionNotFound", message
        )


class ParameterVersionLabelLimitExceeded(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ParameterVersionLabelLimitExceeded, self).__init__(
            "ParameterVersionLabelLimitExceeded", message
        )


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)


class DocumentAlreadyExists(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(DocumentAlreadyExists, self).__init__("DocumentAlreadyExists", message)


class InvalidDocument(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidDocument, self).__init__("InvalidDocument", message)


class InvalidDocumentOperation(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidDocumentOperation, self).__init__(
            "InvalidDocumentOperation", message
        )


class AccessDeniedException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(AccessDeniedException, self).__init__("AccessDeniedException", message)


class InvalidDocumentContent(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidDocumentContent, self).__init__("InvalidDocumentContent", message)


class InvalidDocumentVersion(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidDocumentVersion, self).__init__("InvalidDocumentVersion", message)


class DuplicateDocumentVersionName(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(DuplicateDocumentVersionName, self).__init__(
            "DuplicateDocumentVersionName", message
        )


class DuplicateDocumentContent(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(DuplicateDocumentContent, self).__init__(
            "DuplicateDocumentContent", message
        )
