from __future__ import unicode_literals

import re
import json
import datetime
from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends

from .utils import make_arn_for_certificate

import cryptography.x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


DEFAULT_ACCOUNT_ID = 123456789012
GOOGLE_ROOT_CA = b"""-----BEGIN CERTIFICATE-----
MIIEKDCCAxCgAwIBAgIQAQAhJYiw+lmnd+8Fe2Yn3zANBgkqhkiG9w0BAQsFADBC
MQswCQYDVQQGEwJVUzEWMBQGA1UEChMNR2VvVHJ1c3QgSW5jLjEbMBkGA1UEAxMS
R2VvVHJ1c3QgR2xvYmFsIENBMB4XDTE3MDUyMjExMzIzN1oXDTE4MTIzMTIzNTk1
OVowSTELMAkGA1UEBhMCVVMxEzARBgNVBAoTCkdvb2dsZSBJbmMxJTAjBgNVBAMT
HEdvb2dsZSBJbnRlcm5ldCBBdXRob3JpdHkgRzIwggEiMA0GCSqGSIb3DQEBAQUA
A4IBDwAwggEKAoIBAQCcKgR3XNhQkToGo4Lg2FBIvIk/8RlwGohGfuCPxfGJziHu
Wv5hDbcyRImgdAtTT1WkzoJile7rWV/G4QWAEsRelD+8W0g49FP3JOb7kekVxM/0
Uw30SvyfVN59vqBrb4fA0FAfKDADQNoIc1Fsf/86PKc3Bo69SxEE630k3ub5/DFx
+5TVYPMuSq9C0svqxGoassxT3RVLix/IGWEfzZ2oPmMrhDVpZYTIGcVGIvhTlb7j
gEoQxirsupcgEcc5mRAEoPBhepUljE5SdeK27QjKFPzOImqzTs9GA5eXA37Asd57
r0Uzz7o+cbfe9CUlwg01iZ2d+w4ReYkeN8WvjnJpAgMBAAGjggERMIIBDTAfBgNV
HSMEGDAWgBTAephojYn7qwVkDBF9qn1luMrMTjAdBgNVHQ4EFgQUSt0GFhu89mi1
dvWBtrtiGrpagS8wDgYDVR0PAQH/BAQDAgEGMC4GCCsGAQUFBwEBBCIwIDAeBggr
BgEFBQcwAYYSaHR0cDovL2cuc3ltY2QuY29tMBIGA1UdEwEB/wQIMAYBAf8CAQAw
NQYDVR0fBC4wLDAqoCigJoYkaHR0cDovL2cuc3ltY2IuY29tL2NybHMvZ3RnbG9i
YWwuY3JsMCEGA1UdIAQaMBgwDAYKKwYBBAHWeQIFATAIBgZngQwBAgIwHQYDVR0l
BBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMA0GCSqGSIb3DQEBCwUAA4IBAQDKSeWs
12Rkd1u+cfrP9B4jx5ppY1Rf60zWGSgjZGaOHMeHgGRfBIsmr5jfCnC8vBk97nsz
qX+99AXUcLsFJnnqmseYuQcZZTTMPOk/xQH6bwx+23pwXEz+LQDwyr4tjrSogPsB
E4jLnD/lu3fKOmc2887VJwJyQ6C9bgLxRwVxPgFZ6RGeGvOED4Cmong1L7bHon8X
fOGLVq7uZ4hRJzBgpWJSwzfVO+qFKgE4h6LPcK2kesnE58rF2rwjMvL+GMJ74N87
L9TQEOaWTPtEtyFkDbkAlDASJodYmDkFOA/MgkgMCkdm7r+0X8T/cKjhf4t5K7hl
MqO5tzHpCvX2HzLc
-----END CERTIFICATE-----"""
# Added google root CA as AWS returns chain you gave it + root CA (provided or not)
# so for now a cheap response is just give any old root CA


def datetime_to_epoch(date):
    # As only Py3 has datetime.timestamp()
    return int((date - datetime.datetime(1970, 1, 1)).total_seconds())


class AWSError(Exception):
    TYPE = None
    STATUS = 400

    def __init__(self, message):
        self.message = message

    def response(self):
        resp = {'__type': self.TYPE, 'message': self.message}
        return json.dumps(resp), dict(status=self.STATUS)


class AWSValidationException(AWSError):
    TYPE = 'ValidationException'


class AWSResourceNotFoundException(AWSError):
    TYPE = 'ResourceNotFoundException'


class CertBundle(BaseModel):
    def __init__(self, certificate, private_key, chain=None, region='us-east-1', arn=None, cert_type='IMPORTED'):
        self.created_at = datetime.datetime.now()
        self.cert = certificate
        self._cert = None
        self.common_name = None
        self.key = private_key
        self._key = None
        self.chain = chain
        self.tags = {}
        self._chain = None
        self.type = cert_type  # Should really be an enum

        # AWS always returns your chain + root CA
        if self.chain is None:
            self.chain = GOOGLE_ROOT_CA
        else:
            self.chain += b'\n' + GOOGLE_ROOT_CA

        # Takes care of PEM checking
        self.validate_pk()
        self.validate_certificate()
        if chain is not None:
            self.validate_chain()

        # TODO check cert is valid, or if self-signed then a chain is provided, otherwise
        # raise AWSValidationException('Provided certificate is not a valid self signed. Please provide either a valid self-signed certificate or certificate chain.')

        # Used for when one wants to overwrite an arn
        if arn is None:
            self.arn = make_arn_for_certificate(DEFAULT_ACCOUNT_ID, region)
        else:
            self.arn = arn

    def validate_pk(self):
        try:
            self._key = serialization.load_pem_private_key(self.key, password=None, backend=default_backend())

            if self._key.key_size > 2048:
                AWSValidationException('The private key length is not supported. Only 1024-bit and 2048-bit are allowed.')

        except Exception as err:
            if isinstance(err, AWSValidationException):
                raise
            raise AWSValidationException('The private key is not PEM-encoded or is not valid.')

    def validate_certificate(self):
        try:
            self._cert = cryptography.x509.load_pem_x509_certificate(self.cert, default_backend())

            now = datetime.datetime.now()
            if self._cert.not_valid_after < now:
                raise AWSValidationException('The certificate has expired, is not valid.')

            if self._cert.not_valid_before > now:
                raise AWSValidationException('The certificate is not in effect yet, is not valid.')

            # Extracting some common fields for ease of use
            # Have to search through cert.subject for OIDs
            self.common_name = self._cert.subject.get_attributes_for_oid(cryptography.x509.OID_COMMON_NAME)[0].value

        except Exception as err:
            if isinstance(err, AWSValidationException):
                raise
            raise AWSValidationException('The certificate is not PEM-encoded or is not valid.')

    def validate_chain(self):
        try:
            self._chain = []

            for cert_armored in self.chain.split(b'-\n-'):
                # Would leave encoded but Py2 does not have raw binary strings
                cert_armored = cert_armored.decode()

                # Fix missing -'s on split
                cert_armored = re.sub(r'^----B', '-----B', cert_armored)
                cert_armored = re.sub(r'E----$', 'E-----', cert_armored)
                cert = cryptography.x509.load_pem_x509_certificate(cert_armored.encode(), default_backend())
                self._chain.append(cert)

                now = datetime.datetime.now()
                if self._cert.not_valid_after < now:
                    raise AWSValidationException('The certificate chain has expired, is not valid.')

                if self._cert.not_valid_before > now:
                    raise AWSValidationException('The certificate chain is not in effect yet, is not valid.')

        except Exception as err:
            if isinstance(err, AWSValidationException):
                raise
            raise AWSValidationException('The certificate is not PEM-encoded or is not valid.')

    def describe(self):
        #'RenewalSummary': {},  # Only when cert is amazon issued

        if self._key.key_size == 1024:
            key_algo = 'RSA_1024'
        elif self._key.key_size == 2048:
            key_algo = 'RSA_2048'
        else:
            key_algo = 'EC_prime256v1'

        result = {
            'Certificate': {
                'CertificateArn': self.arn,
                'DomainName': self.common_name,
                'InUseBy': [],
                'Issuer': self._cert.issuer.get_attributes_for_oid(cryptography.x509.OID_COMMON_NAME)[0].value,
                'KeyAlgorithm': key_algo,
                'NotAfter': datetime_to_epoch(self._cert.not_valid_after),
                'NotBefore': datetime_to_epoch(self._cert.not_valid_before),
                'Serial': self._cert.serial,
                'SignatureAlgorithm': self._cert.signature_algorithm_oid._name.upper().replace('ENCRYPTION', ''),
                'Status': 'ISSUED',  # One of PENDING_VALIDATION, ISSUED, INACTIVE, EXPIRED, VALIDATION_TIMED_OUT, REVOKED, FAILED.
                'Subject': 'CN={0}'.format(self.common_name),
                'SubjectAlternativeNames': [],
                'Type': self.type  # One of IMPORTED, AMAZON_ISSUED
            }
        }

        if self.type == 'IMPORTED':
            result['Certificate']['ImportedAt'] = datetime_to_epoch(self.created_at)
        else:
            result['Certificate']['CreatedAt'] = datetime_to_epoch(self.created_at)
            result['Certificate']['IssuedAt'] = datetime_to_epoch(self.created_at)

        return result

    def __str__(self):
        return self.arn

    def __repr__(self):
        return '<Certificate>'


class AWSCertificateManagerBackend(BaseBackend):
    def __init__(self, region):
        super(AWSCertificateManagerBackend, self).__init__()
        self.region = region
        self._certificates = {}

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    def _arn_not_found(self, arn):
        msg = 'Certificate with arn {0} not found in account {1}'.format(arn, DEFAULT_ACCOUNT_ID)
        return AWSResourceNotFoundException(msg)

    def import_cert(self, certificate, private_key, chain=None, arn=None):
        if arn is not None:
            if arn not in self._certificates:
                raise self._arn_not_found(arn)
            else:
                # Will reuse provided ARN
                bundle = CertBundle(certificate, private_key, chain=chain, region=region, arn=arn)
        else:
            # Will generate a random ARN
            bundle = CertBundle(certificate, private_key, chain=chain, region=region)

        self._certificates[bundle.arn] = bundle

        return bundle.arn

    def get_certificates_list(self):
        """
        Get list of certificates

        :return: List of certificates
        :rtype: list of CertBundle
        """
        return self._certificates.values()

    def get_certificate(self, arn):
        if arn not in self._certificates:
            raise self._arn_not_found(arn)

        return self._certificates[arn]

    def delete_certificate(self, arn):
        if arn not in self._certificates:
            raise self._arn_not_found(arn)

        del self._certificates[arn]

    def add_tags_to_certificate(self, arn, tags):
        # get_cert does arn check
        cert_bundle = self.get_certificate(arn)

        for tag in tags:
            key = tag['Key']
            value = tag.get('Value', None)
            cert_bundle.tags[key] = value

    def remove_tags_from_certificate(self, arn, tags):
        # get_cert does arn check
        cert_bundle = self.get_certificate(arn)

        for tag in tags:
            key = tag['Key']
            value = tag.get('Value', None)

            try:
                # If value isnt provided, just delete key
                if value is None:
                    del cert_bundle.tags[key]
                # If value is provided, only delete if it matches what already exists
                elif cert_bundle.tags[key] == value:
                    del cert_bundle.tags[key]
            except KeyError:
                pass


acm_backends = {}
for region, ec2_backend in ec2_backends.items():
    acm_backends[region] = AWSCertificateManagerBackend(region)
