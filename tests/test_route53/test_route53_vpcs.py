import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2, mock_route53


@mock_ec2
@mock_route53
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
    hosted_zone["HostedZone"]["Config"]["PrivateZone"].should.equal(True)
    hosted_zone.should.have.key("VPCs")
    hosted_zone["VPCs"].should.have.length_of(1)
    hosted_zone["VPCs"][0].should.have.key("VPCId")
    hosted_zone["VPCs"][0].should.have.key("VPCRegion")
    hosted_zone["VPCs"][0]["VPCId"].should.be.equal(vpc_id)
    hosted_zone["VPCs"][0]["VPCRegion"].should.be.equal(region)

    hosted_zones = conn.list_hosted_zones()
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones_by_name(DNSName="testdns.aws.com.")
    hosted_zones["HostedZones"].should.have.length_of(1)
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)

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
    hosted_zone["HostedZone"]["Config"]["PrivateZone"].should.equal(True)
    hosted_zone.should.have.key("VPCs")
    hosted_zone["VPCs"].should.have.length_of(0)

    hosted_zones = conn.list_hosted_zones()
    hosted_zones["HostedZones"].should.have.length_of(2)
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)
    hosted_zones["HostedZones"][1]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones_by_name(DNSName=zone2_name)
    hosted_zones["HostedZones"].should.have.length_of(1)
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)
    hosted_zones["HostedZones"][0]["Name"].should.equal(zone2_name)


@mock_ec2
@mock_route53
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
    response.should.have.key("ResponseMetadata")
    response.should.have.key("HostedZoneSummaries")
    response["HostedZoneSummaries"].should.have.length_of(3)

    # Loop through all zone summaries and verify they match what was created
    for summary in response["HostedZoneSummaries"]:
        # use the zone name as the index
        index = summary["Name"].split(".")[1]
        zone_id = zones[index]["HostedZone"]["Id"].split("/")[2]
        summary.should.have.key("HostedZoneId")
        summary["HostedZoneId"].should.equal(zone_id)
        summary.should.have.key("Name")
        summary["Name"].should.equal(zones[index]["HostedZone"]["Name"])


@mock_ec2
@mock_route53
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
    response.should.have.key("ResponseMetadata")
    response.should.have.key("HostedZoneSummaries")
    response["HostedZoneSummaries"].should.have.length_of(1)
    response["HostedZoneSummaries"][0].should.have.key("HostedZoneId")
    retured_zone = response["HostedZoneSummaries"][0]
    retured_zone["HostedZoneId"].should.equal(zone_id)
    retured_zone["Name"].should.equal(zone_b["HostedZone"]["Name"])


@mock_ec2
@mock_route53
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
    resp.should.have.key("ChangeInfo")
    resp["ChangeInfo"].should.have.key("Comment").equals("yolo")


@mock_ec2
@mock_route53
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
    err["Code"].should.equal("PublicZoneVPCAssociation")
    err["Message"].should.equal(
        "You're trying to associate a VPC with a public hosted zone. Amazon Route 53 doesn't support associating a VPC with a public hosted zone."
    )


@mock_ec2
@mock_route53
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
    zone_vpcs.should.have.length_of(2)
    zone_vpcs.should.contain({"VPCRegion": region, "VPCId": vpc_id1})
    zone_vpcs.should.contain({"VPCRegion": region, "VPCId": vpc_id2})

    conn.disassociate_vpc_from_hosted_zone(HostedZoneId=zone_id, VPC={"VPCId": vpc_id1})

    zone_vpcs = conn.get_hosted_zone(Id=zone_id)["VPCs"]
    zone_vpcs.should.have.length_of(1)
    zone_vpcs.should.contain({"VPCRegion": region, "VPCId": vpc_id2})


@mock_ec2
@mock_route53
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
    err["Code"].should.equal("LastVPCAssociation")
    err["Message"].should.equal(
        "The VPC that you're trying to disassociate from the private hosted zone is the last VPC that is associated with the hosted zone. Amazon Route 53 doesn't support disassociating the last VPC from a hosted zone."
    )
