from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_ec2


@mock_ec2
def test_create_route_with_invalid_destination_cidr_block_parameter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    prefix_list = ec2.create_managed_prefix_list(
        AdressFamily="IPV4",
        MaxEntries=10,
        Entries=[{"Cidr": "10.0.0.0/16", "Description": "vpc-a"}],
        PrefixListName="vpc-cidrs",
    )

    assert prefix_list.get("PrefixList").get("AddressFamily") == "IPV4"
    assert prefix_list.get("PrefixList").get("MaxEntries") == 10
    assert prefix_list.get("PrefixList").get("Version") == 1
    assert prefix_list.get("PrefixList").get("PrefixListName") == "vpc-cidrs"
    assert prefix_list.get("PrefixList").get("State") == "create-in-progress"


7a8c64cc26ea4a9790ac48d242de399e7d2b04a1