"""Exceptions raised by the s3control service."""
from moto.core.exceptions import RESTError


ERROR_WITH_ACCESS_POINT_NAME = """{% extends 'wrapped_single_error' %}
{% block extra %}<AccessPointName>{{ name }}</AccessPointName>{% endblock %}
"""


ERROR_WITH_ACCESS_POINT_POLICY = """{% extends 'wrapped_single_error' %}
{% block extra %}<AccessPointName>{{ name }}</AccessPointName>{% endblock %}
"""


class S3ControlError(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "single_error")
        super().__init__(*args, **kwargs)


class AccessPointNotFound(S3ControlError):
    code = 404

    def __init__(self, name, **kwargs):
        kwargs.setdefault("template", "ap_not_found")
        kwargs["name"] = name
        self.templates["ap_not_found"] = ERROR_WITH_ACCESS_POINT_NAME
        super().__init__(
            "NoSuchAccessPoint", "The specified accesspoint does not exist", **kwargs
        )


class AccessPointPolicyNotFound(S3ControlError):
    code = 404

    def __init__(self, name, **kwargs):
        kwargs.setdefault("template", "apf_not_found")
        kwargs["name"] = name
        self.templates["apf_not_found"] = ERROR_WITH_ACCESS_POINT_POLICY
        super().__init__(
            "NoSuchAccessPointPolicy",
            "The specified accesspoint policy does not exist",
            **kwargs
        )
