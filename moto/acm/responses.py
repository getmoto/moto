from __future__ import unicode_literals
import json
import base64

from moto.core.responses import BaseResponse
from .models import acm_backends, AWSError, AWSValidationException


class AWSCertificateManagerResponse(BaseResponse):

    @property
    def acm_backend(self):
        """
        ACM Backend

        :return: ACM Backend object
        :rtype: moto.acm.models.AWSCertificateManagerBackend
        """
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
        arn = self._get_param('CertificateArn')
        tags = self._get_list_prefix('Tags')

        if arn is None:
            msg = 'A required parameter for the specified action is not supplied.'
            return {'__type': 'MissingParameter', 'message': msg}, dict(status=400)

        try:
            self.acm_backend.add_tags_to_certificate(arn, tags)
        except AWSError as err:
            return err.response()

        return ''

    def delete_certificate(self):
        arn = self._get_param('CertificateArn')

        if arn is None:
            msg = 'A required parameter for the specified action is not supplied.'
            return {'__type': 'MissingParameter', 'message': msg}, dict(status=400)

        try:
            self.acm_backend.delete_certificate(arn)
        except AWSError as err:
            return err.response()

        return ''

    def describe_certificate(self):
        raise NotImplementedError()

    def get_certificate(self):
        arn = self._get_param('CertificateArn')

        if arn is None:
            msg = 'A required parameter for the specified action is not supplied.'
            return {'__type': 'MissingParameter', 'message': msg}, dict(status=400)

        try:
            cert_bundle = self.acm_backend.get_certificate(arn)
        except AWSError as err:
            return err.response()

        result = {
            'Certificate': cert_bundle.cert.decode(),
            'CertificateChain': cert_bundle.chain.decode()
        }
        return json.dumps(result)

    def import_certificate(self):
        # TODO comment on what raises exceptions for all branches
        certificate = self._get_param('Certificate')
        private_key = self._get_param('PrivateKey')
        chain = self._get_param('CertificateChain')  # Optional
        current_arn = self._get_param('CertificateArn')  # Optional

        # Simple parameter decoding. Rather do it here as its a data transport decision not part of the
        # actual data
        try:
            certificate = base64.standard_b64decode(certificate)
        except:
            return AWSValidationException('The certificate is not PEM-encoded or is not valid.').response()
        try:
            private_key = base64.standard_b64decode(private_key)
        except:
            return AWSValidationException('The private key is not PEM-encoded or is not valid.').response()
        if chain is not None:
            try:
                chain = base64.standard_b64decode(chain)
            except:
                return AWSValidationException('The certificate chain is not PEM-encoded or is not valid.').response()

        try:
            arn = self.acm_backend.import_cert(certificate, private_key, chain=chain, arn=current_arn)
        except AWSError as err:
            return err.response()

        return json.dumps({'CertificateArn': arn})

    def list_certificates(self):
        certs = []

        for cert_bundle in self.acm_backend.get_certificates_list():
            certs.append({
                'CertificateArn': cert_bundle.arn,
                'DomainName': cert_bundle.common_name
            })

        result = {'CertificateSummaryList': certs}
        return json.dumps(result)

    def list_tags_for_certificate(self):
        arn = self._get_param('CertificateArn')

        if arn is None:
            msg = 'A required parameter for the specified action is not supplied.'
            return {'__type': 'MissingParameter', 'message': msg}, dict(status=400)

        try:
            cert_bundle = self.acm_backend.get_certificate(arn)
        except AWSError as err:
            return err.response()

        result = {'Tags': []}
        # Tag "objects" can not contain the Value part
        for key, value in cert_bundle.tags:
            tag_dict = {'Key': key}
            if value is not None:
                tag_dict['Value'] = value
            result['Tags'].append(tag_dict)

        return json.dumps(result)

    def remove_tags_from_certificate(self):
        arn = self._get_param('CertificateArn')
        tags = self._get_list_prefix('Tags')

        if arn is None:
            msg = 'A required parameter for the specified action is not supplied.'
            return {'__type': 'MissingParameter', 'message': msg}, dict(status=400)

        try:
            self.acm_backend.remove_tags_from_certificate(arn, tags)
        except AWSError as err:
            return err.response()

        return ''

    def request_certificate(self):
        raise NotImplementedError()

    def resend_validation_email(self):
        raise NotImplementedError()
