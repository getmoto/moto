import base64
import re
import datetime
from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import AWSError
from moto.core.utils import BackendDict
from moto import settings

from .utils import make_arn_for_certificate

import cryptography.x509
import cryptography.hazmat.primitives.asymmetric.rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

from moto.core import get_account_id


AWS_ROOT_CA = b"""-----BEGIN CERTIFICATE-----
MIIESTCCAzGgAwIBAgITBntQXCplJ7wevi2i0ZmY7bibLDANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MTAyMTIyMjQzNFoXDTQwMTAyMTIyMjQzNFowRjEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEVMBMGA1UECxMMU2VydmVyIENB
IDFCMQ8wDQYDVQQDEwZBbWF6b24wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
AoIBAQDCThZn3c68asg3Wuw6MLAd5tES6BIoSMzoKcG5blPVo+sDORrMd4f2AbnZ
cMzPa43j4wNxhplty6aUKk4T1qe9BOwKFjwK6zmxxLVYo7bHViXsPlJ6qOMpFge5
blDP+18x+B26A0piiQOuPkfyDyeR4xQghfj66Yo19V+emU3nazfvpFA+ROz6WoVm
B5x+F2pV8xeKNR7u6azDdU5YVX1TawprmxRC1+WsAYmz6qP+z8ArDITC2FMVy2fw
0IjKOtEXc/VfmtTFch5+AfGYMGMqqvJ6LcXiAhqG5TI+Dr0RtM88k+8XUBCeQ8IG
KuANaL7TiItKZYxK1MMuTJtV9IblAgMBAAGjggE7MIIBNzASBgNVHRMBAf8ECDAG
AQH/AgEAMA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUWaRmBlKge5WSPKOUByeW
dFv5PdAwHwYDVR0jBBgwFoAUhBjMhTTsvAyUlC4IWZzHshBOCggwewYIKwYBBQUH
AQEEbzBtMC8GCCsGAQUFBzABhiNodHRwOi8vb2NzcC5yb290Y2ExLmFtYXpvbnRy
dXN0LmNvbTA6BggrBgEFBQcwAoYuaHR0cDovL2NybC5yb290Y2ExLmFtYXpvbnRy
dXN0LmNvbS9yb290Y2ExLmNlcjA/BgNVHR8EODA2MDSgMqAwhi5odHRwOi8vY3Js
LnJvb3RjYTEuYW1hem9udHJ1c3QuY29tL3Jvb3RjYTEuY3JsMBMGA1UdIAQMMAow
CAYGZ4EMAQIBMA0GCSqGSIb3DQEBCwUAA4IBAQAfsaEKwn17DjAbi/Die0etn+PE
gfY/I6s8NLWkxGAOUfW2o+vVowNARRVjaIGdrhAfeWHkZI6q2pI0x/IJYmymmcWa
ZaW/2R7DvQDtxCkFkVaxUeHvENm6IyqVhf6Q5oN12kDSrJozzx7I7tHjhBK7V5Xo
TyS4NU4EhSyzGgj2x6axDd1hHRjblEpJ80LoiXlmUDzputBXyO5mkcrplcVvlIJi
WmKjrDn2zzKxDX5nwvkskpIjYlJcrQu4iCX1/YwZ1yNqF9LryjlilphHCACiHbhI
RnGfN8j8KLDVmWyTYMk8V+6j0LI4+4zFh2upqGMQHL3VFVFWBek6vCDWhB/b
 -----END CERTIFICATE-----"""
# Added aws root CA as AWS returns chain you gave it + root CA (provided or not)
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
        self.in_use_by = []

        # AWS always returns your chain + root CA
        if self.chain is None:
            self.chain = AWS_ROOT_CA
        else:
            self.chain += b"\n" + AWS_ROOT_CA

        # Takes care of PEM checking
        self.validate_pk()
        self.validate_certificate()
        if chain is not None:
            self.validate_chain()

        # TODO check cert is valid, or if self-signed then a chain is provided, otherwise
        # raise AWSValidationException('Provided certificate is not a valid self signed. Please provide either a valid self-signed certificate or certificate chain.')

        # Used for when one wants to overwrite an arn
        if arn is None:
            self.arn = make_arn_for_certificate(get_account_id(), region)
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
                "InUseBy": self.in_use_by,
                "Issuer": self._cert.issuer.get_attributes_for_oid(
                    cryptography.x509.OID_COMMON_NAME
                )[0].value,
                "KeyAlgorithm": key_algo,
                "NotAfter": datetime_to_epoch(self._cert.not_valid_after),
                "NotBefore": datetime_to_epoch(self._cert.not_valid_before),
                "Serial": str(self._cert.serial_number),
                "SignatureAlgorithm": self._cert.signature_algorithm_oid._name.upper().replace(
                    "ENCRYPTION", ""
                ),
                "Status": self.status,  # One of PENDING_VALIDATION, ISSUED, INACTIVE, EXPIRED, VALIDATION_TIMED_OUT, REVOKED, FAILED.
                "Subject": "CN={0}".format(self.common_name),
                "SubjectAlternativeNames": sans,
                "Type": self.type,  # One of IMPORTED, AMAZON_ISSUED,
                "ExtendedKeyUsages": [],
                "RenewalEligibility": "INELIGIBLE",
                "Options": {"CertificateTransparencyLoggingPreference": "ENABLED"},
                "DomainValidationOptions": [{"DomainName": self.common_name}],
            }
        }

        if self.status == "PENDING_VALIDATION":
            result["Certificate"]["DomainValidationOptions"][0][
                "ValidationDomain"
            ] = self.common_name
            result["Certificate"]["DomainValidationOptions"][0][
                "ValidationStatus"
            ] = self.status
            result["Certificate"]["DomainValidationOptions"][0]["ResourceRecord"] = {
                "Name": f"_d930b28be6c5927595552b219965053e.{self.common_name}.",
                "Type": "CNAME",
                "Value": "_c9edd76ee4a0e2a74388032f3861cc50.ykybfrwcxw.acm-validations.aws.",
            }
            result["Certificate"]["DomainValidationOptions"][0][
                "ValidationMethod"
            ] = "DNS"
        if self.type == "IMPORTED":
            result["Certificate"]["ImportedAt"] = datetime_to_epoch(self.created_at)
        else:
            result["Certificate"]["CreatedAt"] = datetime_to_epoch(self.created_at)
            result["Certificate"]["IssuedAt"] = datetime_to_epoch(self.created_at)

        return result

    def serialize_pk(self, passphrase_bytes):
        pk_bytes = self._key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                passphrase_bytes
            ),
        )
        return pk_bytes.decode("utf-8")

    def __str__(self):
        return self.arn

    def __repr__(self):
        return "<Certificate>"


class AWSCertificateManagerBackend(BaseBackend):
    def __init__(self, region):
        super().__init__()
        self.region = region
        self._certificates = {}
        self._idempotency_tokens = {}

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "acm-pca"
        )

    @staticmethod
    def _arn_not_found(arn):
        msg = "Certificate with arn {0} not found in account {1}".format(
            arn, get_account_id()
        )
        return AWSResourceNotFoundException(msg)

    def set_certificate_in_use_by(self, arn, load_balancer_name):
        if arn not in self._certificates:
            raise self._arn_not_found(arn)

        cert_bundle = self._certificates[arn]
        cert_bundle.in_use_by.append(load_balancer_name)

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
        idempotency_token,
        subject_alt_names,
        tags=None,
    ):
        """
        The parameter DomainValidationOptions has not yet been implemented
        """
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

    def export_certificate(self, certificate_arn, passphrase):
        passphrase_bytes = base64.standard_b64decode(passphrase)
        cert_bundle = self.get_certificate(certificate_arn)

        certificate = cert_bundle.cert.decode()
        certificate_chain = cert_bundle.chain.decode()
        private_key = cert_bundle.serialize_pk(passphrase_bytes)

        return certificate, certificate_chain, private_key


acm_backends = BackendDict(AWSCertificateManagerBackend, "ec2")
