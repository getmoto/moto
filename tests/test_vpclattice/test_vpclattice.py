"""Unit tests for vpclattice-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_service():
    client = boto3.client("vpc-lattice", region_name="us-east-2")
    resp = client.create_service(
        name="my-service",
        authType="NONE",
    )
    assert resp["name"] == "my-service"
    assert resp["status"] == "ACTIVE"
    assert resp["arn"].startswith("arn:aws:vpc-lattice:us-east-2:")
    assert resp["dnsEntry"]["hostedZoneId"].startswith("Z")
    assert resp["id"].startswith("srv-")
    assert resp["authType"] == "NONE"

    assert resp["certificateArn"] == ""
    assert resp["customDomainName"] == ""


# @mock_aws
# def test_create_service_network():
#     client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
#     resp = client.create_service_network()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_create_service_network_vpc_association():
#     client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
#     resp = client.create_service_network_vpc_association()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_create_rule():
#     client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
#     resp = client.create_rule()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_tag_resource():
#     client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
#     resp = client.tag_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_tags_for_resource():
#     client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
#     resp = client.list_tags_for_resource()

#     raise Exception("NotYetImplemented")
