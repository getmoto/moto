from moto.core.exceptions import RESTError

EXCEPTION_RESPONSE = """<?xml version="1.0"?>
<ErrorResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <Error>
    <Type>Sender</Type>
    <Code>{{ error_type }}</Code>
    <Message>{{ message }}</Message>
  </Error>
  <{{ request_id_tag }}>30c0dedb-92b1-4e2b-9be4-1188e3ed86ab</{{ request_id_tag }}>
</ErrorResponse>"""


class ElastiCacheException(RESTError):

    code = 400

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "ecerror")
        self.templates["ecerror"] = EXCEPTION_RESPONSE
        super().__init__(*args, **kwargs)


class PasswordTooShort(ElastiCacheException):

    code = 404

    def __init__(self, **kwargs):
        super().__init__(
            "InvalidParameterValue",
            message="Passwords length must be between 16-128 characters.",
            **kwargs,
        )


class PasswordRequired(ElastiCacheException):

    code = 404

    def __init__(self, **kwargs):
        super().__init__(
            "InvalidParameterValue",
            message="No password was provided. If you want to create/update the user without password, please use the NoPasswordRequired flag.",
            **kwargs,
        )


class UserAlreadyExists(ElastiCacheException):

    code = 404

    def __init__(self, **kwargs):
        super().__init__(
            "UserAlreadyExists", message="User user1 already exists.", **kwargs
        )


class UserNotFound(ElastiCacheException):

    code = 404

    def __init__(self, user_id, **kwargs):
        super().__init__("UserNotFound", message=f"User {user_id} not found.", **kwargs)
