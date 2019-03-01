from .exceptions import (
    InvalidRequestException,
)

import binascii
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes


def get_certificate_fingerprint(certificate_pem):
    try:
        cert = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"), default_backend())
    except Exception as err:
        raise InvalidRequestException('Error loading CA certificate, error = {}'.format(err.message))
    return binascii.hexlify(cert.fingerprint(hashes.SHA256()))


def get_ca_arn(region_name, certificate_id):
    return 'arn:aws:iot:%s:1:cacert/%s' % (region_name, certificate_id)
