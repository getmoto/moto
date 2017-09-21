from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import acm_backends


class AWSCertificateManagerResponse(BaseResponse):

    @property
    def acm_backend(self):
        return acm_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, default=None):
        return self.request_params.get(param, default)

    def add_tags_to_certificate(self):
        raise NotImplementedError()

    def delete_certificate(self):
        raise NotImplementedError()

    def describe_certificate(self):
        raise NotImplementedError()

    def import_certificate(self):
        raise NotImplementedError()

    def list_certificates(self):
        raise NotImplementedError()

    def list_tags_for_certificate(self):
        raise NotImplementedError()

    def remove_tags_from_certificate(self):
        raise NotImplementedError()

    def request_certificate(self):
        raise NotImplementedError()

    def resend_validation_email(self):
        raise NotImplementedError()

