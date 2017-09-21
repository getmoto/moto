from __future__ import unicode_literals

import os
import boto3
import sure  # noqa

from botocore.exceptions import ClientError

from moto import mock_acm


RESOURCE_FOLDER = os.path.join(os.path.dirname(__file__), 'resources')
_GET_RESOURCE = lambda x: open(os.path.join(RESOURCE_FOLDER, x), 'rb').read()
CA_CRT = _GET_RESOURCE('ca.pem')
CA_KEY = _GET_RESOURCE('ca.key')
SERVER_CRT = _GET_RESOURCE('star_moto_com.pem')
SERVER_CRT_BAD = _GET_RESOURCE('star_moto_com-bad.pem')
SERVER_KEY = _GET_RESOURCE('star_moto_com.key')


@mock_acm
def test_import_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    resp = client.import_certificate(
        Certificate=SERVER_CRT,
        PrivateKey=SERVER_KEY,
        CertificateChain=CA_CRT
    )
    resp = client.get_certificate(CertificateArn=resp['CertificateArn'])

    print(resp)
