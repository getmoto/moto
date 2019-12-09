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
        arn = self._get_param("CertificateArn")
        tags = self._get_param("Tags")

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return (
                json.dumps({"__type": "MissingParameter", "message": msg}),
                dict(status=400),
            )

        try:
            self.acm_backend.add_tags_to_certificate(arn, tags)
        except AWSError as err:
            return err.response()

        return ""

    def delete_certificate(self):
        arn = self._get_param("CertificateArn")

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return (
                json.dumps({"__type": "MissingParameter", "message": msg}),
                dict(status=400),
            )

        try:
            self.acm_backend.delete_certificate(arn)
        except AWSError as err:
            return err.response()

        return ""

    def describe_certificate(self):
        arn = self._get_param("CertificateArn")

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return (
                json.dumps({"__type": "MissingParameter", "message": msg}),
                dict(status=400),
            )

        try:
            cert_bundle = self.acm_backend.get_certificate(arn)
        except AWSError as err:
            return err.response()

        return json.dumps(cert_bundle.describe())

    def get_certificate(self):
        arn = self._get_param("CertificateArn")

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return (
                json.dumps({"__type": "MissingParameter", "message": msg}),
                dict(status=400),
            )

        try:
            cert_bundle = self.acm_backend.get_certificate(arn)
        except AWSError as err:
            return err.response()

        result = {
            "Certificate": cert_bundle.cert.decode(),
            "CertificateChain": cert_bundle.chain.decode(),
        }
        return json.dumps(result)

    def import_certificate(self):
        """
        Returns errors on:
        Certificate, PrivateKey or Chain not being properly formatted
        Arn not existing if its provided
        PrivateKey size > 2048
        Certificate expired or is not yet in effect

        Does not return errors on:
        Checking Certificate is legit, or a selfsigned chain is provided

        :return: str(JSON) for response
        """
        certificate = self._get_param("Certificate")
        private_key = self._get_param("PrivateKey")
        chain = self._get_param("CertificateChain")  # Optional
        current_arn = self._get_param("CertificateArn")  # Optional

        # Simple parameter decoding. Rather do it here as its a data transport decision not part of the
        # actual data
        try:
            certificate = base64.standard_b64decode(certificate)
        except Exception:
            return AWSValidationException(
                "The certificate is not PEM-encoded or is not valid."
            ).response()
        try:
            private_key = base64.standard_b64decode(private_key)
        except Exception:
            return AWSValidationException(
                "The private key is not PEM-encoded or is not valid."
            ).response()
        if chain is not None:
            try:
                chain = base64.standard_b64decode(chain)
            except Exception:
                return AWSValidationException(
                    "The certificate chain is not PEM-encoded or is not valid."
                ).response()

        try:
            arn = self.acm_backend.import_cert(
                certificate, private_key, chain=chain, arn=current_arn
            )
        except AWSError as err:
            return err.response()

        return json.dumps({"CertificateArn": arn})

    def list_certificates(self):
        certs = []
        statuses = self._get_param("CertificateStatuses")
        for cert_bundle in self.acm_backend.get_certificates_list(statuses):
            certs.append(
                {
                    "CertificateArn": cert_bundle.arn,
                    "DomainName": cert_bundle.common_name,
                }
            )

        result = {"CertificateSummaryList": certs}
        return json.dumps(result)

    def list_tags_for_certificate(self):
        arn = self._get_param("CertificateArn")

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return {"__type": "MissingParameter", "message": msg}, dict(status=400)

        try:
            cert_bundle = self.acm_backend.get_certificate(arn)
        except AWSError as err:
            return err.response()

        result = {"Tags": []}
        # Tag "objects" can not contain the Value part
        for key, value in cert_bundle.tags.items():
            tag_dict = {"Key": key}
            if value is not None:
                tag_dict["Value"] = value
            result["Tags"].append(tag_dict)

        return json.dumps(result)

    def remove_tags_from_certificate(self):
        arn = self._get_param("CertificateArn")
        tags = self._get_param("Tags")

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return (
                json.dumps({"__type": "MissingParameter", "message": msg}),
                dict(status=400),
            )

        try:
            self.acm_backend.remove_tags_from_certificate(arn, tags)
        except AWSError as err:
            return err.response()

        return ""

    def request_certificate(self):
        domain_name = self._get_param("DomainName")
        domain_validation_options = self._get_param(
            "DomainValidationOptions"
        )  # is ignored atm
        idempotency_token = self._get_param("IdempotencyToken")
        subject_alt_names = self._get_param("SubjectAlternativeNames")

        if subject_alt_names is not None and len(subject_alt_names) > 10:
            # There is initial AWS limit of 10
            msg = (
                "An ACM limit has been exceeded. Need to request SAN limit to be raised"
            )
            return (
                json.dumps({"__type": "LimitExceededException", "message": msg}),
                dict(status=400),
            )

        try:
            arn = self.acm_backend.request_certificate(
                domain_name,
                domain_validation_options,
                idempotency_token,
                subject_alt_names,
            )
        except AWSError as err:
            return err.response()

        return json.dumps({"CertificateArn": arn})

    def resend_validation_email(self):
        arn = self._get_param("CertificateArn")
        domain = self._get_param("Domain")
        # ValidationDomain not used yet.
        # Contains domain which is equal to or a subset of Domain
        # that AWS will send validation emails to
        # https://docs.aws.amazon.com/acm/latest/APIReference/API_ResendValidationEmail.html
        # validation_domain = self._get_param('ValidationDomain')

        if arn is None:
            msg = "A required parameter for the specified action is not supplied."
            return (
                json.dumps({"__type": "MissingParameter", "message": msg}),
                dict(status=400),
            )

        try:
            cert_bundle = self.acm_backend.get_certificate(arn)

            if cert_bundle.common_name != domain:
                msg = "Parameter Domain does not match certificate domain"
                _type = "InvalidDomainValidationOptionsException"
                return json.dumps({"__type": _type, "message": msg}), dict(status=400)

        except AWSError as err:
            return err.response()

        return ""
