from __future__ import unicode_literals

import re
import datetime
from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import AWSError
from moto.ec2 import ec2_backends
from moto import settings

from .utils import make_arn_for_certificate

import cryptography.x509
import cryptography.hazmat.primitives.asymmetric.rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

from moto.core import ACCOUNT_ID as DEFAULT_ACCOUNT_ID


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


class AWSValidationException(AWSError):
    TYPE = "ValidationException"


class AWSResourceNotFoundException(AWSError):
    TYPE = "ResourceNotFoundException"


class AWSTooManyTagsException(AWSError):
    TYPE = "TooManyTagsException"


class TagHolder(dict):
    MAX_TAG_COUNT = 50
    MAX_KEY_LENGTH = 128
    MAX_VALUE_LENGTH = 256

    def _validate_kv(self, key, value, index):
        if len(key) > self.MAX_KEY_LENGTH:
            raise AWSValidationException(
                "Value '%s' at 'tags.%d.member.key' failed to satisfy constraint: Member must have length less than or equal to %s"
                % (key, index, self.MAX_KEY_LENGTH)
            )
        if value and len(value) > self.MAX_VALUE_LENGTH:
            raise AWSValidationException(
                "Value '%s' at 'tags.%d.member.value' failed to satisfy constraint: Member must have length less than or equal to %s"
                % (value, index, self.MAX_VALUE_LENGTH)
            )
        if key.startswith("aws:"):
            raise AWSValidationException(
                'Invalid Tag Key: "%s". AWS internal tags cannot be changed with this API'
                % key
            )

    def add(self, tags):
        tags_copy = self.copy()
        for i, tag in enumerate(tags):
            key = tag["Key"]
            value = tag.get("Value", None)
            self._validate_kv(key, value, i + 1)

            tags_copy[key] = value
        if len(tags_copy) > self.MAX_TAG_COUNT:
            raise AWSTooManyTagsException(
                "the TagSet: '{%s}' contains too many Tags"
                % ", ".join(k + "=" + str(v or "") for k, v in tags_copy.items())
            )

        self.update(tags_copy)

    def remove(self, tags):
        for i, tag in enumerate(tags):
            key = tag["Key"]
            value = tag.get("Value", None)
            self._validate_kv(key, value, i + 1)
            try:
                # If value isnt provided, just delete key
                if value is None:
                    del self[key]
                # If value is provided, only delete if it matches what already exists
                elif self[key] == value:
                    del self[key]
            except KeyError:
                pass

    def equals(self, tags):
        tags = {t["Key"]: t.get("Value", None) for t in tags} if tags else {}
        return self == tags


class CertBundle(BaseModel):
    def __init__(
        self,
        certificate,
        private_key,
        chain=None,
        region="us-east-1",
        arn=None,
        cert_type="IMPORTED",
        cert_status="ISSUED",
    ):
        self.created_at = datetime.datetime.now()
        self.cert = certificate
        self._cert = None
        self.common_name = None
        self.key = private_key
        self._key = None
        self.chain = chain
        self.tags = TagHolder()
        self._chain = None
        self.type = cert_type  # Should really be an enum
        self.status = cert_status  # Should really be an enum

        # AWS always returns your chain + root CA
        if self.chain is None:
            self.chain = GOOGLE_ROOT_CA
        else:
            self.chain += b"\n" + GOOGLE_ROOT_CA

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

    @classmethod
    def generate_cert(cls, domain_name, region, sans=None):
        if sans is None:
            sans = set()
        else:
            sans = set(sans)

        sans.add(domain_name)
        sans = [cryptography.x509.DNSName(item) for item in sans]

        key = cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        subject = cryptography.x509.Name(
            [
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.COUNTRY_NAME, "US"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.STATE_OR_PROVINCE_NAME, "CA"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.LOCALITY_NAME, "San Francisco"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.ORGANIZATION_NAME, "My Company"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.COMMON_NAME, domain_name
                ),
            ]
        )
        issuer = cryptography.x509.Name(
            [  # C = US, O = Amazon, OU = Server CA 1B, CN = Amazon
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.COUNTRY_NAME, "US"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.ORGANIZATION_NAME, "Amazon"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.ORGANIZATIONAL_UNIT_NAME, "Server CA 1B"
                ),
                cryptography.x509.NameAttribute(
                    cryptography.x509.NameOID.COMMON_NAME, "Amazon"
                ),
            ]
        )
        cert = (
            cryptography.x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(cryptography.x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                cryptography.x509.SubjectAlternativeName(sans), critical=False
            )
            .sign(key, hashes.SHA512(), default_backend())
        )

        cert_armored = cert.public_bytes(serialization.Encoding.PEM)
        private_key = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cls(
            cert_armored,
            private_key,
            cert_type="AMAZON_ISSUED",
            cert_status="PENDING_VALIDATION",
            region=region,
        )

    def validate_pk(self):
        try:
            self._key = serialization.load_pem_private_key(
                self.key, password=None, backend=default_backend()
            )

            if self._key.key_size > 2048:
                AWSValidationException(
                    "The private key length is not supported. Only 1024-bit and 2048-bit are allowed."
                )

        except Exception as err:
            if isinstance(err, AWSValidationException):
                raise
            raise AWSValidationException(
                "The private key is not PEM-encoded or is not valid."
            )

    def validate_certificate(self):
        try:
            self._cert = cryptography.x509.load_pem_x509_certificate(
                self.cert, default_backend()
            )

            now = datetime.datetime.utcnow()
            if self._cert.not_valid_after < now:
                raise AWSValidationException(
                    "The certificate has expired, is not valid."
                )

            if self._cert.not_valid_before > now:
                raise AWSValidationException(
                    "The certificate is not in effect yet, is not valid."
                )

            # Extracting some common fields for ease of use
            # Have to search through cert.subject for OIDs
            self.common_name = self._cert.subject.get_attributes_for_oid(
                cryptography.x509.OID_COMMON_NAME
            )[0].value

        except Exception as err:
            if isinstance(err, AWSValidationException):
                raise
            raise AWSValidationException(
                "The certificate is not PEM-encoded or is not valid."
            )

    def validate_chain(self):
        try:
            self._chain = []

            for cert_armored in self.chain.split(b"-\n-"):
                # Would leave encoded but Py2 does not have raw binary strings
                cert_armored = cert_armored.decode()

                # Fix missing -'s on split
                cert_armored = re.sub(r"^----B", "-----B", cert_armored)
                cert_armored = re.sub(r"E----$", "E-----", cert_armored)
                cert = cryptography.x509.load_pem_x509_certificate(
                    cert_armored.encode(), default_backend()
                )
                self._chain.append(cert)

                now = datetime.datetime.now()
                if self._cert.not_valid_after < now:
                    raise AWSValidationException(
                        "The certificate chain has expired, is not valid."
                    )

                if self._cert.not_valid_before > now:
                    raise AWSValidationException(
                        "The certificate chain is not in effect yet, is not valid."
                    )

        except Exception as err:
            if isinstance(err, AWSValidationException):
                raise
            raise AWSValidationException(
                "The certificate is not PEM-encoded or is not valid."
            )

    def check(self):
        # Basically, if the certificate is pending, and then checked again after a
        # while, it will appear as if its been validated. The default wait time is 60
        # seconds but you can set an environment to change it.
        waited_seconds = (datetime.datetime.now() - self.created_at).total_seconds()
        if (
            self.type == "AMAZON_ISSUED"
            and self.status == "PENDING_VALIDATION"
            and waited_seconds > settings.ACM_VALIDATION_WAIT
        ):
            self.status = "ISSUED"

    def describe(self):
        # 'RenewalSummary': {},  # Only when cert is amazon issued
        if self._key.key_size == 1024:
            key_algo = "RSA_1024"
        elif self._key.key_size == 2048:
            key_algo = "RSA_2048"
        else:
            key_algo = "EC_prime256v1"

        # Look for SANs
        try:
            san_obj = self._cert.extensions.get_extension_for_oid(
                cryptography.x509.OID_SUBJECT_ALTERNATIVE_NAME
            )
        except cryptography.x509.ExtensionNotFound:
            san_obj = None
        sans = []
        if san_obj is not None:
            sans = [item.value for item in san_obj.value]

        result = {
            "Certificate": {
                "CertificateArn": self.arn,
                "DomainName": self.common_name,
                "InUseBy": [],
                "Issuer": self._cert.issuer.get_attributes_for_oid(
                    cryptography.x509.OID_COMMON_NAME
                )[0].value,
                "KeyAlgorithm": key_algo,
                "NotAfter": datetime_to_epoch(self._cert.not_valid_after),
                "NotBefore": datetime_to_epoch(self._cert.not_valid_before),
                "Serial": self._cert.serial_number,
                "SignatureAlgorithm": self._cert.signature_algorithm_oid._name.upper().replace(
                    "ENCRYPTION", ""
                ),
                "Status": self.status,  # One of PENDING_VALIDATION, ISSUED, INACTIVE, EXPIRED, VALIDATION_TIMED_OUT, REVOKED, FAILED.
                "Subject": "CN={0}".format(self.common_name),
                "SubjectAlternativeNames": sans,
                "Type": self.type,  # One of IMPORTED, AMAZON_ISSUED
            }
        }

        if self.type == "IMPORTED":
            result["Certificate"]["ImportedAt"] = datetime_to_epoch(self.created_at)
        else:
            result["Certificate"]["CreatedAt"] = datetime_to_epoch(self.created_at)
            result["Certificate"]["IssuedAt"] = datetime_to_epoch(self.created_at)

        return result

    def __str__(self):
        return self.arn

    def __repr__(self):
        return "<Certificate>"


class AWSCertificateManagerBackend(BaseBackend):
    def __init__(self, region):
        super(AWSCertificateManagerBackend, self).__init__()
        self.region = region
        self._certificates = {}
        self._idempotency_tokens = {}

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @staticmethod
    def _arn_not_found(arn):
        msg = "Certificate with arn {0} not found in account {1}".format(
            arn, DEFAULT_ACCOUNT_ID
        )
        return AWSResourceNotFoundException(msg)

    def _get_arn_from_idempotency_token(self, token):
        """
        If token doesnt exist, return None, later it will be
        set with an expiry and arn.

        If token expiry has passed, delete entry and return None

        Else return ARN

        :param token: String token
        :return: None or ARN
        """
        now = datetime.datetime.now()
        if token in self._idempotency_tokens:
            if self._idempotency_tokens[token]["expires"] < now:
                # Token has expired, new request
                del self._idempotency_tokens[token]
                return None
            else:
                return self._idempotency_tokens[token]["arn"]

        return None

    def _set_idempotency_token_arn(self, token, arn):
        self._idempotency_tokens[token] = {
            "arn": arn,
            "expires": datetime.datetime.now() + datetime.timedelta(hours=1),
        }

    def import_cert(self, certificate, private_key, chain=None, arn=None, tags=None):
        if arn is not None:
            if arn not in self._certificates:
                raise self._arn_not_found(arn)
            else:
                # Will reuse provided ARN
                bundle = CertBundle(
                    certificate, private_key, chain=chain, region=self.region, arn=arn
                )
        else:
            # Will generate a random ARN
            bundle = CertBundle(
                certificate, private_key, chain=chain, region=self.region
            )

        self._certificates[bundle.arn] = bundle

        if tags:
            self.add_tags_to_certificate(bundle.arn, tags)

        return bundle.arn

    def get_certificates_list(self, statuses):
        """
        Get list of certificates

        :return: List of certificates
        :rtype: list of CertBundle
        """
        for arn in self._certificates.keys():
            cert = self.get_certificate(arn)
            if not statuses or cert.status in statuses:
                yield cert

    def get_certificate(self, arn):
        if arn not in self._certificates:
            raise self._arn_not_found(arn)

        cert_bundle = self._certificates[arn]
        cert_bundle.check()
        return cert_bundle

    def delete_certificate(self, arn):
        if arn not in self._certificates:
            raise self._arn_not_found(arn)

        del self._certificates[arn]

    def request_certificate(
        self,
        domain_name,
        domain_validation_options,
        idempotency_token,
        subject_alt_names,
        tags=None,
    ):
        if idempotency_token is not None:
            arn = self._get_arn_from_idempotency_token(idempotency_token)
            if arn and self._certificates[arn].tags.equals(tags):
                return arn

        cert = CertBundle.generate_cert(
            domain_name, region=self.region, sans=subject_alt_names
        )
        if idempotency_token is not None:
            self._set_idempotency_token_arn(idempotency_token, cert.arn)
        self._certificates[cert.arn] = cert

        if tags:
            cert.tags.add(tags)

        return cert.arn

    def add_tags_to_certificate(self, arn, tags):
        # get_cert does arn check
        cert_bundle = self.get_certificate(arn)
        cert_bundle.tags.add(tags)

    def remove_tags_from_certificate(self, arn, tags):
        # get_cert does arn check
        cert_bundle = self.get_certificate(arn)
        cert_bundle.tags.remove(tags)


acm_backends = {}
for region, ec2_backend in ec2_backends.items():
    acm_backends[region] = AWSCertificateManagerBackend(region)
