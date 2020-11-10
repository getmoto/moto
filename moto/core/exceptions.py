from __future__ import unicode_literals

from werkzeug.exceptions import HTTPException
from jinja2 import DictLoader, Environment
import json


SINGLE_ERROR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>{{error_type}}</Code>
    <Message>{{message}}</Message>
    {% block extra %}{% endblock %}
    <RequestID>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestID>
</Error>
"""

ERROR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
  <ErrorResponse>
    <Errors>
      <Error>
        <Code>{{error_type}}</Code>
        <Message>{{message}}</Message>
        {% block extra %}{% endblock %}
      </Error>
    </Errors>
  <RequestID>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestID>
</ErrorResponse>
"""

ERROR_JSON_RESPONSE = """{
    "message": "{{message}}",
    "__type": "{{error_type}}"
}
"""


class RESTError(HTTPException):
    code = 400

    templates = {
        "single_error": SINGLE_ERROR_RESPONSE,
        "error": ERROR_RESPONSE,
        "error_json": ERROR_JSON_RESPONSE,
    }

    def __init__(self, error_type, message, template="error", **kwargs):
        super(RESTError, self).__init__()
        env = Environment(loader=DictLoader(self.templates))
        self.error_type = error_type
        self.message = message
        self.description = env.get_template(template).render(
            error_type=error_type, message=message, **kwargs
        )


class DryRunClientError(RESTError):
    code = 400


class JsonRESTError(RESTError):
    def __init__(self, error_type, message, template="error_json", **kwargs):
        super(JsonRESTError, self).__init__(error_type, message, template, **kwargs)

    def get_headers(self, *args, **kwargs):
        return [("Content-Type", "application/json")]

    def get_body(self, *args, **kwargs):
        return self.description


class SignatureDoesNotMatchError(RESTError):
    code = 403

    def __init__(self):
        super(SignatureDoesNotMatchError, self).__init__(
            "SignatureDoesNotMatch",
            "The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.",
        )


class InvalidClientTokenIdError(RESTError):
    code = 403

    def __init__(self):
        super(InvalidClientTokenIdError, self).__init__(
            "InvalidClientTokenId",
            "The security token included in the request is invalid.",
        )


class AccessDeniedError(RESTError):
    code = 403

    def __init__(self, user_arn, action):
        super(AccessDeniedError, self).__init__(
            "AccessDenied",
            "User: {user_arn} is not authorized to perform: {operation}".format(
                user_arn=user_arn, operation=action
            ),
        )


class AuthFailureError(RESTError):
    code = 401

    def __init__(self):
        super(AuthFailureError, self).__init__(
            "AuthFailure",
            "AWS was not able to validate the provided access credentials",
        )


class AWSError(Exception):
    TYPE = None
    STATUS = 400

    def __init__(self, message, type=None, status=None):
        self.message = message
        self.type = type if type is not None else self.TYPE
        self.status = status if status is not None else self.STATUS

    def response(self):
        return (
            json.dumps({"__type": self.type, "message": self.message}),
            dict(status=self.status),
        )


class InvalidNextTokenException(JsonRESTError):
    """For AWS Config resource listing. This will be used by many different resource types, and so it is in moto.core."""

    code = 400

    def __init__(self):
        super(InvalidNextTokenException, self).__init__(
            "InvalidNextTokenException", "The nextToken provided is invalid"
        )
