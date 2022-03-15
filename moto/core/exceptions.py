from werkzeug.exceptions import HTTPException
from jinja2 import DictLoader, Environment
import json

# TODO: add "<Type>Sender</Type>" to error responses below?


SINGLE_ERROR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>{{error_type}}</Code>
    <Message>{{message}}</Message>
    {% block extra %}{% endblock %}
    <{{request_id_tag}}>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</{{request_id_tag}}>
</Error>
"""

WRAPPED_SINGLE_ERROR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ErrorResponse{% if xmlns is defined %} xmlns="{{xmlns}}"{% endif %}>
    <Error>
        <Code>{{error_type}}</Code>
        <Message>{{message}}</Message>
        {% block extra %}{% endblock %}
        <{{request_id_tag}}>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</{{request_id_tag}}>
    </Error>
</ErrorResponse>"""

ERROR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
  <ErrorResponse>
    <Errors>
      <Error>
        <Code>{{error_type}}</Code>
        <Message><![CDATA[{{message}}]]></Message>
        {% block extra %}{% endblock %}
      </Error>
    </Errors>
  <{{request_id_tag}}>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</{{request_id_tag}}>
</ErrorResponse>
"""


class RESTError(HTTPException):
    code = 400
    # most APIs use <RequestId>, but some APIs (including EC2, S3) use <RequestID>
    request_id_tag_name = "RequestId"

    templates = {
        "single_error": SINGLE_ERROR_RESPONSE,
        "wrapped_single_error": WRAPPED_SINGLE_ERROR_RESPONSE,
        "error": ERROR_RESPONSE,
    }

    def __init__(self, error_type, message, template="error", **kwargs):
        super().__init__()
        self.error_type = error_type
        self.message = message

        if template in self.templates.keys():
            env = Environment(loader=DictLoader(self.templates))
            self.description = env.get_template(template).render(
                error_type=error_type,
                message=message,
                request_id_tag=self.request_id_tag_name,
                **kwargs
            )
            self.content_type = "application/xml"

    def get_headers(self, *args, **kwargs):  # pylint: disable=unused-argument
        return {
            "X-Amzn-ErrorType": self.error_type or "UnknownError",
            "Content-Type": self.content_type,
        }

    def get_body(self, *args, **kwargs):  # pylint: disable=unused-argument
        return self.description


class DryRunClientError(RESTError):
    code = 412


class JsonRESTError(RESTError):
    def __init__(self, error_type, message, template="error_json", **kwargs):
        super().__init__(error_type, message, template, **kwargs)
        self.description = json.dumps(
            {"__type": self.error_type, "message": self.message}
        )
        self.content_type = "application/json"

    def get_body(self, *args, **kwargs):
        return self.description


class SignatureDoesNotMatchError(RESTError):
    code = 403

    def __init__(self):
        super().__init__(
            "SignatureDoesNotMatch",
            "The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.",
        )


class InvalidClientTokenIdError(RESTError):
    code = 403

    def __init__(self):
        super().__init__(
            "InvalidClientTokenId",
            "The security token included in the request is invalid.",
        )


class AccessDeniedError(RESTError):
    code = 403

    def __init__(self, user_arn, action):
        super().__init__(
            "AccessDenied",
            "User: {user_arn} is not authorized to perform: {operation}".format(
                user_arn=user_arn, operation=action
            ),
        )


class AuthFailureError(RESTError):
    code = 401

    def __init__(self):
        super().__init__(
            "AuthFailure",
            "AWS was not able to validate the provided access credentials",
        )


class AWSError(JsonRESTError):
    TYPE = None
    STATUS = 400

    def __init__(self, message, exception_type=None, status=None):
        super().__init__(exception_type or self.TYPE, message)
        self.code = status or self.STATUS


class InvalidNextTokenException(JsonRESTError):
    """For AWS Config resource listing. This will be used by many different resource types, and so it is in moto.core."""

    code = 400

    def __init__(self):
        super().__init__(
            "InvalidNextTokenException", "The nextToken provided is invalid"
        )


class InvalidToken(AWSError):
    code = 400

    def __init__(self, message="Invalid token"):
        super().__init__("Invalid Token: {}".format(message), "InvalidToken")
