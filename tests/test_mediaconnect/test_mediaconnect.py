from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_mediaconnect


region = "eu-west-1"


def _create_flow_config(name, **kwargs):
    availability_zone = kwargs.get("availability_zone", "AZ1")
    entitlements = kwargs.get(
        "entitlements",
        [
            {
                "DataTransferSubscriberFeePercent": 12,
                "Description": "An entitlement",
                "Encryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
                "EntitlementStatus": "ENABLED",
                "Name": "Entitlement A",
                "Subscribers": [],
            }
        ],
    )
    outputs = kwargs.get("outputs", [{"Name": "Output 1", "Protocol": "zixi-push"}])
    source = kwargs.get(
        "source",
        {
            "Decryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
            "Description": "A source",
            "Name": "Source A",
        },
    )
    source_failover_config = kwargs.get("source_failover_config", {})
    sources = kwargs.get("sources", [])
    vpc_interfaces = kwargs.get("vpc_interfaces", [])
    flow_config = dict(
        AvailabilityZone=availability_zone,
        Entitlements=entitlements,
        Name=name,
        Outputs=outputs,
        Source=source,
        SourceFailoverConfig=source_failover_config,
        Sources=sources,
        VpcInterfaces=vpc_interfaces,
    )
    return flow_config


@mock_mediaconnect
def test_create_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test Flow 1")

    response = client.create_flow(**channel_config)

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Flow"]["FlowArn"][:26].should.equal("arn:aws:mediaconnect:flow:")
    response["Flow"]["Name"].should.equal("test Flow 1")
    response["Flow"]["Status"].should.equal("STANDBY")
