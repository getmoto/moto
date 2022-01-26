import boto3

from moto import mock_route53


@mock_route53
def test_get_dnssec():
    client = boto3.client("route53", region_name="ap-southeast-1")
    zone_id = client.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True),
    )["HostedZone"]["Id"]

    resp = client.get_dnssec(HostedZoneId=zone_id)

    resp.should.have.key("Status")
    resp["Status"].should.have.key("ServeSignature").equals("NOT_SIGNING")
    resp["Status"].should.have.key("StatusMessage").equals("")

    resp.should.have.key("KeySigningKeys").equals([])
