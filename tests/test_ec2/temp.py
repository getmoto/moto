import base64
import ipaddress
import json
import os
import warnings
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID

decode_method = base64.decodebytes

@mock_aws
def test_modify_instance_metadata_options():
    import pdb
    ec2 = boto3.client("ec2", region_name="us-west-2")
    volume_tags = [
        {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
        {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
    ]
    instances = ec2.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[{"ResourceType": "volume", "Tags": volume_tags}],
        MetadataOptions={"HttpEndpoint": "Enabled"}
    ).get("Instances")
    instance_id = [i["InstanceId"] for i in instances]
    import pdb
    pdb.set_trace()
    # To test(changing the defaults)
    ec2.modify_instance_metadata_options(
        InstanceId=instance_id[0],
        HttpTokens='required',
        HttpPutResponseHopLimit=2,
        HttpEndpoint='disabled',
        DryRun=False,
        HttpProtocolIpv6='enabled',
        InstanceMetadataTags='enabled'
    )

