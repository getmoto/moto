from __future__ import unicode_literals

import boto3
import sure  # noqa
from nose.tools import assert_raises
from botocore.exceptions import ClientError
from moto import mock_iotdata, mock_iot


@mock_iot
@mock_iotdata
def test():
    iot_client = boto3.client('iot')
    client = boto3.client('iot-data')
    name = 'my-thing'
    payload = b'{"state": {"desired": {}}}'
    iot_client.create_thing(thingName=name)

    with assert_raises(ClientError):
        client.get_thing_shadow(thingName=name)
    client.update_thing_shadow(thingName=name, payload=payload)
    client.get_thing_shadow(thingName=name)

    client.delete_thing_shadow(thingName=name)
    with assert_raises(ClientError):
        client.get_thing_shadow(thingName=name)
