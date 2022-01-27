import boto3

from moto import mock_route53


@mock_route53
def test_list_hosted_zones_by_vpc():
    client = boto3.client("route53", region_name="us-east-2")
    resp = client.list_hosted_zones_by_vpc(VPCId="unknown", VPCRegion="us-east-2")
    resp.should.have.key("HostedZoneSummaries").equals([])


@mock_route53
def test_associate_vpc_with_hosted_zone():
    client = boto3.client("route53", region_name="us-east-2")

    zone_id = client.create_hosted_zone(
        Name="vpc.zone",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True),
    )["HostedZone"]["Id"]

    resp = client.associate_vpc_with_hosted_zone(
        HostedZoneId=zone_id, VPC={"VPCRegion": "us-east-1", "VPCId": "myvpc"}
    )

    resp.should.have.key("ChangeInfo")
    resp["ChangeInfo"].should.have.key("Id")
    resp["ChangeInfo"].should.have.key("Status").equals("INSYNC")
    resp["ChangeInfo"].should.have.key("SubmittedAt")


@mock_route53
def test_associate_vpc_and_list():
    client = boto3.client("route53", region_name="us-east-2")

    zone_id = client.create_hosted_zone(
        Name="vpc.zone",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True),
    )["HostedZone"]["Id"]

    client.associate_vpc_with_hosted_zone(
        HostedZoneId=zone_id, VPC={"VPCRegion": "us-east-1", "VPCId": "myvpc"}
    )

    # Hosted zone can be found using the (unvalidated) VPC ID
    resp = client.list_hosted_zones_by_vpc(VPCId="myvpc", VPCRegion="us-east-1")
    resp.should.have.key("HostedZoneSummaries").equals(
        [{"HostedZoneId": zone_id, "Name": "vpc.zone."}]
    )

    # No hosted zones are present in other regions
    resp = client.list_hosted_zones_by_vpc(VPCId="myvpc", VPCRegion="us-west-1")
    resp.should.have.key("HostedZoneSummaries").equals([])


@mock_route53
def test_disassociate_vpc_and_list():
    client = boto3.client("route53", region_name="us-east-2")

    zone_id = client.create_hosted_zone(
        Name="vpc.zone",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True),
    )["HostedZone"]["Id"]

    client.associate_vpc_with_hosted_zone(
        HostedZoneId=zone_id, VPC={"VPCRegion": "us-east-1", "VPCId": "myvpc"}
    )

    client.disassociate_vpc_from_hosted_zone(
        HostedZoneId=zone_id, VPC={"VPCRegion": "us-east-1", "VPCId": "myvpc"}
    )

    # Hosted zone can no longer be found
    resp = client.list_hosted_zones_by_vpc(VPCId="myvpc", VPCRegion="us-east-1")
    resp.should.have.key("HostedZoneSummaries").equals([])
