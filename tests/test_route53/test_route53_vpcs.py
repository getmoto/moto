import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_hosted_zone_private_zone_preserved():
    # Create mock VPC so we can get a VPC ID
    region = "us-east-1"
    ec2c = boto3.client("ec2", region_name=region)
    vpc_id = ec2c.create_vpc(CidrBlock="10.1.0.0/16").get("Vpc").get("VpcId")

    # Create hosted_zone as a Private VPC Hosted Zone
    conn = boto3.client("route53", region_name=region)
    new_zone = conn.create_hosted_zone(
        Name="testdns.aws.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="Test"),
        VPC={"VPCRegion": region, "VPCId": vpc_id},
    )

    zone_id = new_zone["HostedZone"]["Id"].split("/")[-1]
    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    assert hosted_zone["HostedZone"]["Config"]["PrivateZone"]

    assert len(hosted_zone["VPCs"]) == 1
    assert hosted_zone["VPCs"][0]["VPCId"] == vpc_id
    assert hosted_zone["VPCs"][0]["VPCRegion"] == region

    hosted_zones = conn.list_hosted_zones()
    assert hosted_zones["HostedZones"][0]["Config"]["PrivateZone"]

    hosted_zones = conn.list_hosted_zones_by_name(DNSName="testdns.aws.com.")
    assert len(hosted_zones["HostedZones"]) == 1
    assert hosted_zones["HostedZones"][0]["Config"]["PrivateZone"]

    # create_hosted_zone statements with  PrivateZone=True,
    # but without a _valid_ vpc-id should NOT fail.
    zone2_name = "testdns2.aws.com."
    no_vpc_zone = conn.create_hosted_zone(
        Name=zone2_name,
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="Test without VPC"),
    )

    zone_id = no_vpc_zone["HostedZone"]["Id"].split("/")[-1]
    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    assert hosted_zone["HostedZone"]["Config"]["PrivateZone"]

    assert len(hosted_zone["VPCs"]) == 0

    hosted_zones = conn.list_hosted_zones()
    assert len(hosted_zones["HostedZones"]) == 2
    assert hosted_zones["HostedZones"][0]["Config"]["PrivateZone"]
    assert hosted_zones["HostedZones"][1]["Config"]["PrivateZone"]

    hosted_zones = conn.list_hosted_zones_by_name(DNSName=zone2_name)
    assert len(hosted_zones["HostedZones"]) == 1
    assert hosted_zones["HostedZones"][0]["Config"]["PrivateZone"]
    assert hosted_zones["HostedZones"][0]["Name"] == zone2_name


@mock_aws
def test_list_hosted_zones_by_vpc_with_multiple_vpcs():
    # Create mock VPC so we can get a VPC ID
    ec2c = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2c.create_vpc(CidrBlock="10.1.0.0/16").get("Vpc").get("VpcId")
    region = "us-east-1"

    # Create 3 Zones associate with the VPC.
    zones = {}
    conn = boto3.client("route53", region_name=region)
    for zone in ["a", "b", "c"]:
        zone_name = f"test.{zone}.com."
        zones[zone] = conn.create_hosted_zone(
            Name=zone_name,
            CallerReference=str(hash("foo")),
            HostedZoneConfig=dict(PrivateZone=True, Comment=f"test {zone} com"),
            VPC={"VPCRegion": region, "VPCId": vpc_id},
        )

    # List the zones associated with this vpc
    response = conn.list_hosted_zones_by_vpc(VPCId=vpc_id, VPCRegion=region)
    assert len(response["HostedZoneSummaries"]) == 3

    # Loop through all zone summaries and verify they match what was created
    for summary in response["HostedZoneSummaries"]:
        # use the zone name as the index
        index = summary["Name"].split(".")[1]
        zone_id = zones[index]["HostedZone"]["Id"].split("/")[2]
        assert summary["HostedZoneId"] == zone_id
        assert summary["Name"] == zones[index]["HostedZone"]["Name"]


@mock_aws
def test_list_hosted_zones_by_vpc():
    # Create mock VPC so we can get a VPC ID
    ec2c = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2c.create_vpc(CidrBlock="10.1.0.0/16").get("Vpc").get("VpcId")
    region = "us-east-1"

    conn = boto3.client("route53", region_name=region)
    zone_b = conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test com"),
        VPC={"VPCRegion": region, "VPCId": vpc_id},
    )
    zone_id = zone_b["HostedZone"]["Id"].split("/")[2]

    response = conn.list_hosted_zones_by_vpc(VPCId=vpc_id, VPCRegion=region)
    assert len(response["HostedZoneSummaries"]) == 1
    returned_zone = response["HostedZoneSummaries"][0]
    assert returned_zone["HostedZoneId"] == zone_id
    assert returned_zone["Name"] == zone_b["HostedZone"]["Name"]


@mock_aws
def test_route53_associate_vpc():
    ec2c = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2c.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]["VpcId"]
    conn = boto3.client("route53", region_name="us-east-1")
    zone = conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment=""),
    )
    zone_id = zone["HostedZone"]["Id"].split("/")[2]

    resp = conn.associate_vpc_with_hosted_zone(
        HostedZoneId=zone_id,
        VPC={"VPCId": vpc_id, "VPCRegion": "us-east-1"},
        Comment="yolo",
    )
    assert resp["ChangeInfo"]["Comment"] == "yolo"


@mock_aws
def test_route53_associate_vpc_with_public_Zone():
    ec2c = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2c.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]["VpcId"]
    conn = boto3.client("route53", region_name="us-east-1")
    zone = conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
    )
    zone_id = zone["HostedZone"]["Id"].split("/")[2]

    with pytest.raises(ClientError) as exc:
        conn.associate_vpc_with_hosted_zone(
            HostedZoneId=zone_id,
            VPC={"VPCId": vpc_id, "VPCRegion": "us-east-1"},
            Comment="yolo",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PublicZoneVPCAssociation"
    assert (
        err["Message"]
        == "You're trying to associate a VPC with a public hosted zone. Amazon Route 53 doesn't support associating a VPC with a public hosted zone."
    )


@mock_aws
def test_route53_associate_and_disassociate_vpc():
    ec2c = boto3.client("ec2", region_name="us-east-1")
    vpc_id1 = ec2c.create_vpc(CidrBlock="10.1.0.0/16").get("Vpc").get("VpcId")
    vpc_id2 = ec2c.create_vpc(CidrBlock="10.1.0.1/16").get("Vpc").get("VpcId")
    region = "us-east-1"

    conn = boto3.client("route53", region_name=region)
    zone = conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test com"),
        VPC={"VPCRegion": region, "VPCId": vpc_id1},
    )
    zone_id = zone["HostedZone"]["Id"].split("/")[2]

    conn.associate_vpc_with_hosted_zone(
        HostedZoneId=zone_id,
        VPC={"VPCId": vpc_id2, "VPCRegion": region},
    )

    zone_vpcs = conn.get_hosted_zone(Id=zone_id)["VPCs"]
    assert len(zone_vpcs) == 2
    assert {"VPCRegion": region, "VPCId": vpc_id1} in zone_vpcs
    assert {"VPCRegion": region, "VPCId": vpc_id2} in zone_vpcs

    conn.disassociate_vpc_from_hosted_zone(HostedZoneId=zone_id, VPC={"VPCId": vpc_id1})

    zone_vpcs = conn.get_hosted_zone(Id=zone_id)["VPCs"]
    assert len(zone_vpcs) == 1
    assert {"VPCRegion": region, "VPCId": vpc_id2} in zone_vpcs


@mock_aws
def test_route53_disassociate_last_vpc():
    ec2c = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2c.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]["VpcId"]
    conn = boto3.client("route53", region_name="us-east-1")
    zone = conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test com"),
        VPC={"VPCRegion": "us-east-1", "VPCId": vpc_id},
    )
    zone_id = zone["HostedZone"]["Id"].split("/")[2]

    with pytest.raises(ClientError) as exc:
        conn.disassociate_vpc_from_hosted_zone(
            HostedZoneId=zone_id, VPC={"VPCId": vpc_id}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "LastVPCAssociation"
    assert (
        err["Message"]
        == "The VPC that you're trying to disassociate from the private hosted zone is the last VPC that is associated with the hosted zone. Amazon Route 53 doesn't support disassociating the last VPC from a hosted zone."
    )
