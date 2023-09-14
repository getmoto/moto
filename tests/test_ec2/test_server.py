"""Test the different server responses."""
import re
import xmltodict

import moto.server as server
from tests import EXAMPLE_AMI_ID


def test_ec2_server_get():
    backend = server.create_backend_app("ec2")
    test_client = backend.test_client()

    res = test_client.get(
        "/?Action=RunInstances&ImageId=" + EXAMPLE_AMI_ID,
        headers={"Host": "ec2.us-east-1.amazonaws.com"},
    )

    groups = re.search("<instanceId>(.*)</instanceId>", res.data.decode("utf-8"))
    instance_id = groups.groups()[0]

    res = test_client.get("/?Action=DescribeInstances")
    assert instance_id in res.data.decode("utf-8")


def test_ec2_get_unknown_vpc():
    """
    Ensure that this call returns the error format in the right format
    Terraform will throw errors when destroying a VPC otherwise
    :return:
    """
    backend = server.create_backend_app("ec2")
    test_client = backend.test_client()

    res = test_client.get(
        "/?Action=DescribeVpcs&VpcId.1=vpc-unknown",
        headers={"Host": "ec2.us-east-1.amazonaws.com"},
    )

    assert res.status_code == 400
    body = xmltodict.parse(res.data.decode("utf-8"), dict_constructor=dict)
    assert "Response" in body
    assert "Errors" in body["Response"]
    assert "Error" in body["Response"]["Errors"]
    error = body["Response"]["Errors"]["Error"]
    assert error["Code"] == "InvalidVpcID.NotFound"
    assert error["Message"] == "VpcID {'vpc-unknown'} does not exist."


def test_ec2_get_unknown_route_table():
    """
    Ensure that this call returns the error format in the right format
    Terraform will throw errors when destroying a RouteTable otherwise
    :return:
    """
    backend = server.create_backend_app("ec2")
    test_client = backend.test_client()

    res = test_client.get(
        "/?Action=DescribeRouteTables&RouteTableId.1=rtb-unknown",
        headers={"Host": "ec2.us-east-1.amazonaws.com"},
    )

    assert res.status_code == 400
    body = xmltodict.parse(res.data.decode("utf-8"), dict_constructor=dict)
    assert "Error" in body["Response"]["Errors"]
    error = body["Response"]["Errors"]["Error"]
    assert error["Code"] == "InvalidRouteTableID.NotFound"
    assert error["Message"] == "The routeTable ID 'rtb-unknown' does not exist"
