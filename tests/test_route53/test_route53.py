import boto3
import botocore
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings


@mock_aws
def test_create_hosted_zone():
    conn = boto3.client("route53", region_name="us-east-1")
    response = conn.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )
    firstzone = response["HostedZone"]
    assert "/hostedzone/" in firstzone["Id"]
    assert firstzone["Name"] == "testdns.aws.com."
    assert firstzone["Config"] == {"PrivateZone": False}
    assert firstzone["ResourceRecordSetCount"] == 2

    delegation = response["DelegationSet"]
    assert len(delegation["NameServers"]) == 4
    assert "ns-2048.awsdns-64.com" in delegation["NameServers"]
    assert "ns-2049.awsdns-65.net" in delegation["NameServers"]
    assert "ns-2050.awsdns-66.org" in delegation["NameServers"]
    assert "ns-2051.awsdns-67.co.uk" in delegation["NameServers"]

    location = response["Location"]
    if not settings.TEST_SERVER_MODE:
        assert "<Name>testdns.aws.com.</Name>" in requests.get(location).text


@mock_aws
def test_get_hosted_zone():
    conn = boto3.client("route53", region_name="us-east-1")
    name = "testdns.aws.com."
    caller_ref = str(hash("foo"))

    zone = conn.create_hosted_zone(Name=name, CallerReference=caller_ref)["HostedZone"]

    res = conn.get_hosted_zone(Id=zone["Id"])
    assert res["HostedZone"]["Name"] == name
    assert res["HostedZone"]["CallerReference"] == caller_ref


@mock_aws
def test_list_hosted_zones():
    conn = boto3.client("route53", region_name="us-east-1")

    res = conn.list_hosted_zones()["HostedZones"]
    assert len(res) == 0

    zone1 = conn.create_hosted_zone(
        Name="testdns1.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]
    zone2 = conn.create_hosted_zone(
        Name="testdns2.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]

    res = conn.list_hosted_zones()["HostedZones"]
    assert len(res) == 2

    assert zone1 in res
    assert zone2 in res


@mock_aws
def test_delete_hosted_zone():
    conn = boto3.client("route53", region_name="us-east-1")

    zone1 = conn.create_hosted_zone(
        Name="testdns1.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]
    conn.create_hosted_zone(Name="testdns2.aws.com.", CallerReference=str(hash("foo")))

    conn.delete_hosted_zone(Id=zone1["Id"])

    res = conn.list_hosted_zones()["HostedZones"]
    assert len(res) == 1


@mock_aws
def test_delete_hosted_zone_with_change_sets():
    conn = boto3.client("route53", region_name="us-east-1")

    zone_id = conn.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]["Id"]

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "foo.bar.testdns.aws.com",
                        "Type": "A",
                        "ResourceRecords": [{"Value": "1.2.3.4"}],
                    },
                }
            ]
        },
    )

    with pytest.raises(ClientError) as exc:
        conn.delete_hosted_zone(Id=zone_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "HostedZoneNotEmpty"
    assert (
        err["Message"]
        == "The hosted zone contains resource records that are not SOA or NS records."
    )


@mock_aws
def test_get_hosted_zone_count_no_zones():
    conn = boto3.client("route53", region_name="us-east-1")
    zone_count = conn.get_hosted_zone_count()
    assert zone_count["HostedZoneCount"] == 0


@mock_aws
def test_get_hosted_zone_count_one_zone():
    conn = boto3.client("route53", region_name="us-east-1")
    zone = "a"
    zone_name = f"test.{zone}.com."
    conn.create_hosted_zone(
        Name=zone_name,
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment=f"test {zone} com"),
    )
    zone_count = conn.get_hosted_zone_count()
    assert zone_count["HostedZoneCount"] == 1


@mock_aws
def test_get_hosted_zone_count_many_zones():
    conn = boto3.client("route53", region_name="us-east-1")
    zones = {}
    zone_indexes = []
    for char in range(ord("a"), ord("d") + 1):
        for char2 in range(ord("a"), ord("z") + 1):
            zone_indexes.append(f"{chr(char)}{chr(char2)}")

    # Create 100-ish zones and make sure we get 100 back.  This works
    # for 702 zones {a..zz}, but seemed a needless waste of
    # time/resources.
    for zone in zone_indexes:
        zone_name = f"test.{zone}.com."
        zones[zone] = conn.create_hosted_zone(
            Name=zone_name,
            CallerReference=str(hash("foo")),
            HostedZoneConfig=dict(PrivateZone=False, Comment=f"test {zone} com"),
        )
    zone_count = conn.get_hosted_zone_count()
    assert zone_count["HostedZoneCount"] == len(zone_indexes)


@mock_aws
def test_get_unknown_hosted_zone():
    conn = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_hosted_zone(Id="unknown")

    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchHostedZone"
    assert err["Message"] == "No hosted zone found with ID: unknown"


@mock_aws
def test_update_hosted_zone_comment():
    conn = boto3.client("route53", region_name="us-east-1")
    response = conn.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )
    zone_id = response["HostedZone"]["Id"].split("/")[-1]

    conn.update_hosted_zone_comment(Id=zone_id, Comment="yolo")

    resp = conn.get_hosted_zone(Id=zone_id)["HostedZone"]
    assert resp["Config"]["Comment"] == "yolo"


@mock_aws
def test_list_resource_record_set_unknown_zone():
    conn = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_resource_record_sets(HostedZoneId="abcd")

    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchHostedZone"
    assert err["Message"] == "No hosted zone found with ID: abcd"


@mock_aws
def test_list_resource_record_set_unknown_type():
    conn = boto3.client("route53", region_name="us-east-1")
    zone = conn.create_hosted_zone(
        Name="testdns1.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]

    with pytest.raises(ClientError) as ex:
        conn.list_resource_record_sets(HostedZoneId=zone["Id"], StartRecordType="A")

    err = ex.value.response["Error"]
    assert err["Code"] == "400"
    assert err["Message"] == "Bad Request"


@mock_aws
def test_use_health_check_in_resource_record_set():
    conn = boto3.client("route53", region_name="us-east-1")

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]
    check_id = check["Id"]

    zone = conn.create_hosted_zone(
        Name="testdns.aws.com", CallerReference=str(hash("foo"))
    )
    zone_id = zone["HostedZone"]["Id"]

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "foo.bar.testdns.aws.com",
                        "Type": "A",
                        "HealthCheckId": check_id,
                        "ResourceRecords": [{"Value": "1.2.3.4"}],
                    },
                }
            ]
        },
    )

    record_sets = conn.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    assert record_sets[2]["Name"] == "foo.bar.testdns.aws.com."
    assert record_sets[2]["HealthCheckId"] == check_id


@mock_aws
def test_hosted_zone_comment_preserved():
    conn = boto3.client("route53", region_name="us-east-1")

    firstzone = conn.create_hosted_zone(
        Name="testdns.aws.com",
        CallerReference=str(hash("foo")),
        HostedZoneConfig={"Comment": "test comment"},
    )
    zone_id = firstzone["HostedZone"]["Id"]

    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    assert hosted_zone["HostedZone"]["Config"]["Comment"] == "test comment"

    hosted_zones = conn.list_hosted_zones()
    assert hosted_zones["HostedZones"][0]["Config"]["Comment"] == "test comment"


@mock_aws
def test_deleting_weighted_route():
    conn = boto3.client("route53", region_name="us-east-1")

    zone = conn.create_hosted_zone(
        Name="testdns.aws.com", CallerReference=str(hash("foo"))
    )
    zone_id = zone["HostedZone"]["Id"]

    for identifier in ["success-test-foo", "success-test-bar"]:
        conn.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "cname.testdns.aws.com",
                            "Type": "CNAME",
                            "SetIdentifier": identifier,
                            "Weight": 50,
                        },
                    }
                ]
            },
        )

    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    assert len(cnames) == 4

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": "cname.testdns.aws.com",
                        "Type": "CNAME",
                        "SetIdentifier": "success-test-foo",
                        "Weight": 50,
                    },
                }
            ]
        },
    )

    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    assert len(cnames) == 3
    assert cnames[-1]["Name"] == "cname.testdns.aws.com."
    assert cnames[-1]["SetIdentifier"] == "success-test-bar"


@mock_aws
def test_deleting_latency_route():
    conn = boto3.client("route53", region_name="us-east-1")

    zone = conn.create_hosted_zone(
        Name="testdns.aws.com", CallerReference=str(hash("foo"))
    )
    zone_id = zone["HostedZone"]["Id"]

    for _id, region in [
        ("success-test-foo", "us-west-2"),
        ("success-test-bar", "us-west-1"),
    ]:
        conn.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "cname.testdns.aws.com",
                            "Type": "CNAME",
                            "SetIdentifier": _id,
                            "Region": region,
                            "ResourceRecords": [{"Value": "example.com"}],
                        },
                    }
                ]
            },
        )

    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    assert len(cnames) == 4
    foo_cname = [
        cname
        for cname in cnames
        if cname.get("SetIdentifier") and cname["SetIdentifier"] == "success-test-foo"
    ][0]
    assert foo_cname["Region"] == "us-west-2"

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": "cname.testdns.aws.com",
                        "Type": "CNAME",
                        "SetIdentifier": "success-test-foo",
                        "Region": "us-west-2",
                        "ResourceRecords": [{"Value": "example.com"}],
                    },
                }
            ]
        },
    )
    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    assert len(cnames) == 3
    assert cnames[-1]["SetIdentifier"] == "success-test-bar"
    assert cnames[-1]["Region"] == "us-west-1"


@mock_aws
def test_list_or_change_tags_for_resource_request():
    conn = boto3.client("route53", region_name="us-east-1")
    health_check = conn.create_health_check(
        CallerReference="foobar",
        HealthCheckConfig={
            "IPAddress": "192.0.2.44",
            "Port": 123,
            "Type": "HTTP",
            "ResourcePath": "/",
            "RequestInterval": 30,
            "FailureThreshold": 123,
            "HealthThreshold": 123,
        },
    )
    healthcheck_id = health_check["HealthCheck"]["Id"]

    # confirm this works for resources with zero tags
    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    assert response["ResourceTagSet"]["Tags"] == []

    tag1 = {"Key": "Deploy", "Value": "True"}
    tag2 = {"Key": "Name", "Value": "UnitTest"}

    # Test adding a tag for a resource id
    conn.change_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id, AddTags=[tag1, tag2]
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    assert "ResourceTagSet" in response

    # Validate that each key was added
    assert tag1 in response["ResourceTagSet"]["Tags"]
    assert tag2 in response["ResourceTagSet"]["Tags"]

    assert len(response["ResourceTagSet"]["Tags"]) == 2

    # Try to remove the tags
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag1["Key"]],
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    assert "ResourceTagSet" in response
    assert tag1 not in response["ResourceTagSet"]["Tags"]
    assert tag2 in response["ResourceTagSet"]["Tags"]

    # Remove the second tag
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag2["Key"]],
    )

    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    assert tag2 not in response["ResourceTagSet"]["Tags"]

    # Re-add the tags
    conn.change_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id, AddTags=[tag1, tag2]
    )

    # Remove both
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag1["Key"], tag2["Key"]],
    )

    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    assert response["ResourceTagSet"]["Tags"] == []


@mock_aws
def test_list_tags_for_resources():
    conn = boto3.client("route53", region_name="us-east-1")
    zone1 = conn.create_hosted_zone(
        Name="testdns1.aws.com", CallerReference=str(hash("foo"))
    )
    zone1_id = zone1["HostedZone"]["Id"]
    zone2 = conn.create_hosted_zone(
        Name="testdns2.aws.com", CallerReference=str(hash("bar"))
    )
    zone2_id = zone2["HostedZone"]["Id"]

    # confirm this works for resources with zero tags
    response = conn.list_tags_for_resources(
        ResourceIds=[zone1_id, zone2_id], ResourceType="hostedzone"
    )

    for set in response["ResourceTagSets"]:
        assert set["Tags"] == []

    tag1 = {"Key": "Deploy", "Value": "True"}
    tag2 = {"Key": "Name", "Value": "UnitTest"}
    tag3 = {"Key": "Owner", "Value": "Alice"}
    tag4 = {"Key": "License", "Value": "MIT"}

    conn.change_tags_for_resource(
        ResourceType="hostedzone", ResourceId=zone1_id, AddTags=[tag1, tag2]
    )
    conn.change_tags_for_resource(
        ResourceType="hostedzone", ResourceId=zone2_id, AddTags=[tag3, tag4]
    )

    response = conn.list_tags_for_resources(
        ResourceIds=[zone1_id, zone2_id], ResourceType="hostedzone"
    )
    for set in response["ResourceTagSets"]:
        if set["ResourceId"] == zone1_id:
            assert tag1 in set["Tags"]
            assert tag2 in set["Tags"]
        elif set["ResourceId"] == zone2_id:
            assert tag3 in set["Tags"]
            assert tag4 in set["Tags"]


@mock_aws
def test_list_hosted_zones_by_name():
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

    zone_b = conn.list_hosted_zones_by_name(DNSName="test.b.com.")
    assert len(zone_b["HostedZones"]) == 1
    assert zone_b["HostedZones"][0]["Name"] == "test.b.com."
    assert zone_b["HostedZones"][0]["Config"]["PrivateZone"]

    # We declared this a a private hosted zone above, so let's make
    # sure it really is!
    zone_b_id = zone_b["HostedZones"][0]["Id"].split("/")[-1]
    b_hosted_zone = conn.get_hosted_zone(Id=zone_b_id)

    # Pull the HostedZone block out and test it.
    b_hz = b_hosted_zone["HostedZone"]
    assert b_hz["Config"]["PrivateZone"]

    # Check for the VPCs block since this *should* be a VPC-Private Zone
    assert len(b_hosted_zone["VPCs"]) == 1
    b_hz_vpcs = b_hosted_zone["VPCs"][0]
    assert b_hz_vpcs["VPCId"] == vpc_id
    assert b_hz_vpcs["VPCRegion"] == region

    # Now create other zones and test them.
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test org"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test org 2"),
    )

    # Now makes sure the other zones we created above are NOT private...
    zones = conn.list_hosted_zones_by_name(DNSName="test.a.org.")
    assert len(zones["HostedZones"]) == 2
    assert zones["HostedZones"][0]["Name"] == "test.a.org."
    assert zones["HostedZones"][0]["Config"]["PrivateZone"] is False

    assert zones["HostedZones"][1]["Name"] == "test.a.org."
    assert zones["HostedZones"][1]["Config"]["PrivateZone"] is False

    # test sort order
    zones = conn.list_hosted_zones_by_name()
    assert len(zones["HostedZones"]) == 3
    assert zones["HostedZones"][0]["Name"] == "test.b.com."
    assert zones["HostedZones"][1]["Name"] == "test.a.org."
    assert zones["HostedZones"][2]["Name"] == "test.a.org."


@mock_aws
def test_list_hosted_zones_by_dns_name():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test com"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test org"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test org 2"),
    )
    conn.create_hosted_zone(
        Name="my.test.net.",
        CallerReference=str(hash("baz")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test net"),
    )

    # test lookup
    zones = conn.list_hosted_zones_by_name(DNSName="test.b.com.")
    assert len(zones["HostedZones"]) == 1
    assert zones["DNSName"] == "test.b.com."
    zones = conn.list_hosted_zones_by_name(DNSName="test.a.org.")
    assert len(zones["HostedZones"]) == 2
    assert zones["DNSName"] == "test.a.org."
    zones = conn.list_hosted_zones_by_name(DNSName="my.test.net.")
    assert len(zones["HostedZones"]) == 1
    assert zones["DNSName"] == "my.test.net."
    zones = conn.list_hosted_zones_by_name(DNSName="my.test.net")
    assert len(zones["HostedZones"]) == 1
    assert zones["DNSName"] == "my.test.net."

    # test sort order
    zones = conn.list_hosted_zones_by_name()
    assert len(zones["HostedZones"]) == 4
    assert zones["HostedZones"][0]["Name"] == "test.b.com."
    assert zones["HostedZones"][0]["CallerReference"] == str(hash("foo"))
    assert zones["HostedZones"][1]["Name"] == "my.test.net."
    assert zones["HostedZones"][1]["CallerReference"] == str(hash("baz"))
    assert zones["HostedZones"][2]["Name"] == "test.a.org."
    assert zones["HostedZones"][2]["CallerReference"] == str(hash("bar"))
    assert zones["HostedZones"][3]["Name"] == "test.a.org."
    assert zones["HostedZones"][3]["CallerReference"] == str(hash("bar"))


@mock_aws
def test_list_hosted_zones_pagination():
    conn = boto3.client("route53", region_name="us-east-1")

    for idx in range(150):
        conn.create_hosted_zone(
            Name=f"test{idx}.com.", CallerReference=str(hash(f"h{idx}"))
        )

    page1 = conn.list_hosted_zones()
    assert "Marker" not in page1
    assert page1["IsTruncated"] is True
    assert "NextMarker" in page1
    assert "MaxItems" not in page1
    assert len(page1["HostedZones"]) == 100

    page2 = conn.list_hosted_zones(Marker=page1["NextMarker"])
    assert page2["Marker"] == page1["NextMarker"]
    assert page2["IsTruncated"] is False
    assert "NextMarker" not in page2
    assert "MaxItems" not in page2
    assert len(page2["HostedZones"]) == 50

    small_page = conn.list_hosted_zones(MaxItems="75")
    assert "Marker" not in small_page
    assert small_page["IsTruncated"] is True
    assert "NextMarker" in small_page
    assert small_page["MaxItems"] == "75"
    assert len(small_page["HostedZones"]) == 75

    remainer = conn.list_hosted_zones(Marker=small_page["NextMarker"])
    assert remainer["Marker"] == small_page["NextMarker"]
    assert remainer["IsTruncated"] is False
    assert "NextMarker" not in remainer
    assert "MaxItems" not in remainer
    assert len(remainer["HostedZones"]) == 75


@mock_aws
def test_change_resource_record_sets_crud_valid():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    assert len(zones["HostedZones"]) == 1
    assert zones["HostedZones"][0]["Name"] == "db."
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create A Record.
    a_record_endpoint_payload = {
        "Comment": "Create A record prod.redis.db",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=a_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 3
    a_record_detail = response["ResourceRecordSets"][2]
    assert a_record_detail["Name"] == "prod.redis.db."
    assert a_record_detail["Type"] == "A"
    assert a_record_detail["TTL"] == 10
    assert a_record_detail["ResourceRecords"] == [{"Value": "127.0.0.1"}]

    # Update A Record.
    cname_record_endpoint_payload = {
        "Comment": "Update A record prod.redis.db",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 60,
                    "ResourceRecords": [{"Value": "192.168.1.1"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=cname_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 3
    cname_record_detail = response["ResourceRecordSets"][2]
    assert cname_record_detail["Name"] == "prod.redis.db."
    assert cname_record_detail["Type"] == "A"
    assert cname_record_detail["TTL"] == 60
    assert cname_record_detail["ResourceRecords"] == [{"Value": "192.168.1.1"}]

    # Update to add Alias.
    cname_alias_record_endpoint_payload = {
        "Comment": "Update to Alias prod.redis.db",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 60,
                    "AliasTarget": {
                        "HostedZoneId": hosted_zone_id,
                        "DNSName": "prod.redis.alias.",
                        "EvaluateTargetHealth": False,
                    },
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=cname_alias_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    cname_alias_record_detail = response["ResourceRecordSets"][2]
    assert cname_alias_record_detail["Name"] == "prod.redis.db."
    assert cname_alias_record_detail["Type"] == "A"
    assert cname_alias_record_detail["TTL"] == 60
    assert cname_alias_record_detail["AliasTarget"] == {
        "HostedZoneId": hosted_zone_id,
        "DNSName": "prod.redis.alias.",
        "EvaluateTargetHealth": False,
    }
    assert "ResourceRecords" not in cname_alias_record_detail

    # Delete record.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 60,
                    "ResourceRecords": [{"Value": "192.168.1.1"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 2


@mock_aws
@pytest.mark.parametrize("multi_value_answer", [True, False, None])
def test_change_resource_record_sets_crud_valid_with_special_xml_chars(
    multi_value_answer,
):
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    assert len(zones["HostedZones"]) == 1
    assert zones["HostedZones"][0]["Name"] == "db."
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create TXT Record.
    txt_record_endpoint_payload = {
        "Comment": "Create TXT record prod.redis.db",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "TXT",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "SomeInitialValue"}],
                },
            }
        ],
    }
    if multi_value_answer is not None:
        txt_record_endpoint_payload["Changes"][0]["ResourceRecordSet"][
            "MultiValueAnswer"
        ] = multi_value_answer
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=txt_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 3
    a_record_detail = response["ResourceRecordSets"][2]
    assert a_record_detail["Name"] == "prod.redis.db."
    assert a_record_detail["Type"] == "TXT"
    assert a_record_detail["TTL"] == 10
    assert a_record_detail["ResourceRecords"] == [{"Value": "SomeInitialValue"}]

    # Update TXT Record with XML Special Character &.
    txt_record_with_special_char_endpoint_payload = {
        "Comment": "Update TXT record prod.redis.db",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "TXT",
                    "TTL": 60,
                    "ResourceRecords": [{"Value": "SomeInitialValue&NewValue"}],
                },
            }
        ],
    }
    if multi_value_answer is not None:
        txt_record_with_special_char_endpoint_payload["Changes"][0][
            "ResourceRecordSet"
        ]["MultiValueAnswer"] = multi_value_answer
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch=txt_record_with_special_char_endpoint_payload,
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 3
    cname_record_detail = response["ResourceRecordSets"][2]
    assert cname_record_detail["Name"] == "prod.redis.db."
    assert cname_record_detail["Type"] == "TXT"
    assert cname_record_detail["TTL"] == 60
    assert cname_record_detail["ResourceRecords"] == [
        {"Value": "SomeInitialValue&NewValue"}
    ]
    assert cname_record_detail.get("MultiValueAnswer") == multi_value_answer

    # Delete record.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "TXT",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "SomeInitialValue"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 2


@mock_aws
def test_change_resource_record_set__delete_should_match_create():
    # To delete a resource record set, you must specify all the same values that you specified when you created it.
    client = boto3.client("route53", region_name="us-east-1")
    name = "example.com"
    hosted_zone_id = client.create_hosted_zone(Name=name, CallerReference=name)[
        "HostedZone"
    ]["Id"]

    client.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": name,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": "192.168.0.1"}],
                    },
                }
            ]
        },
    )

    with pytest.raises(ClientError) as exc:
        client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "DELETE",
                        "ResourceRecordSet": {
                            "Name": name,
                            "Type": "A",
                            # Missing TTL and ResourceRecords
                        },
                    }
                ]
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert (
        err["Message"]
        == "Invalid request: Expected exactly one of [AliasTarget, all of [TTL, and ResourceRecords], or TrafficPolicyInstanceId], but found none in Change with [Action=DELETE, Name=example.com, Type=A, SetIdentifier=null]"
    )


@mock_aws
def test_change_weighted_resource_record_sets():
    conn = boto3.client("route53", region_name="us-east-2")
    conn.create_hosted_zone(
        Name="test.vpc.internal.", CallerReference=str(hash("test"))
    )

    zones = conn.list_hosted_zones_by_name(DNSName="test.vpc.internal.")

    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create 2 weighted records
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "test.vpc.internal",
                        "Type": "A",
                        "SetIdentifier": "test1",
                        "Weight": 50,
                        "AliasTarget": {
                            "HostedZoneId": "Z3AADJGX6KTTL2",
                            "DNSName": "internal-test1lb-447688172.us-east-2.elb.amazonaws.com.",
                            "EvaluateTargetHealth": True,
                        },
                    },
                },
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "test.vpc.internal",
                        "Type": "A",
                        "SetIdentifier": "test2",
                        "Weight": 50,
                        "AliasTarget": {
                            "HostedZoneId": "Z3AADJGX6KTTL2",
                            "DNSName": "internal-testlb2-1116641781.us-east-2.elb.amazonaws.com.",
                            "EvaluateTargetHealth": True,
                        },
                    },
                },
            ]
        },
    )

    rr_sets = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)[
        "ResourceRecordSets"
    ]
    record = [r for r in rr_sets if r["Type"] == "A"][0]
    # Update the first record to have a weight of 90
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record["Name"],
                        "Type": record["Type"],
                        "SetIdentifier": record["SetIdentifier"],
                        "Weight": 90,
                        "AliasTarget": {
                            "HostedZoneId": record["AliasTarget"]["HostedZoneId"],
                            "DNSName": record["AliasTarget"]["DNSName"],
                            "EvaluateTargetHealth": record["AliasTarget"][
                                "EvaluateTargetHealth"
                            ],
                        },
                    },
                }
            ]
        },
    )

    record = [r for r in rr_sets if r["Type"] == "A"][1]
    # Update the second record to have a weight of 10
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record["Name"],
                        "Type": record["Type"],
                        "SetIdentifier": record["SetIdentifier"],
                        "Weight": 10,
                        "AliasTarget": {
                            "HostedZoneId": record["AliasTarget"]["HostedZoneId"],
                            "DNSName": record["AliasTarget"]["DNSName"],
                            "EvaluateTargetHealth": record["AliasTarget"][
                                "EvaluateTargetHealth"
                            ],
                        },
                    },
                }
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    for record in response["ResourceRecordSets"]:
        if record.get("SetIdentifier"):
            if record["SetIdentifier"] == "test1":
                assert record["Weight"] == 90
            if record["SetIdentifier"] == "test2":
                assert record["Weight"] == 10


@mock_aws
def test_failover_record_sets():
    conn = boto3.client("route53", region_name="us-east-2")
    conn.create_hosted_zone(Name="test.zone.", CallerReference=str(hash("test")))
    zones = conn.list_hosted_zones_by_name(DNSName="test.zone.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create geolocation record
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "failover.test.zone.",
                        "Type": "A",
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.1"}],
                        "Failover": "PRIMARY",
                    },
                }
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    record = response["ResourceRecordSets"][2]
    assert record["Failover"] == "PRIMARY"


@mock_aws
def test_geolocation_record_sets():
    conn = boto3.client("route53", region_name="us-east-2")
    conn.create_hosted_zone(Name="test.zone.", CallerReference=str(hash("test")))
    zones = conn.list_hosted_zones_by_name(DNSName="test.zone.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create geolocation record
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "georecord1.test.zone.",
                        "Type": "A",
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.1"}],
                        "GeoLocation": {"ContinentCode": "EU"},
                    },
                },
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "georecord2.test.zone.",
                        "Type": "A",
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.2"}],
                        "GeoLocation": {"CountryCode": "US", "SubdivisionCode": "NY"},
                    },
                },
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    rrs = response["ResourceRecordSets"]
    assert rrs[2]["GeoLocation"] == {"ContinentCode": "EU"}
    assert rrs[3]["GeoLocation"] == {"CountryCode": "US", "SubdivisionCode": "NY"}


@mock_aws
def test_change_resource_record_invalid():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    assert len(zones["HostedZones"]) == 1
    assert zones["HostedZones"][0]["Name"] == "db."
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    invalid_a_record_payload = {
        "Comment": "this should fail",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "prod.scooby.doo",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }

    with pytest.raises(botocore.exceptions.ClientError):
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=invalid_a_record_payload
        )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 2

    invalid_cname_record_payload = {
        "Comment": "this should also fail",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.scooby.doo",
                    "Type": "CNAME",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }

    with pytest.raises(botocore.exceptions.ClientError):
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=invalid_cname_record_payload
        )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 2


@mock_aws
def test_change_resource_record_invalid_action_value():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    assert len(zones["HostedZones"]) == 1
    assert zones["HostedZones"][0]["Name"] == "db."
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    invalid_a_record_payload = {
        "Comment": "this should fail",
        "Changes": [
            {
                "Action": "INVALID_ACTION",
                "ResourceRecordSet": {
                    "Name": "prod.scooby.doo",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=invalid_a_record_payload
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert (
        err["Message"]
        == "Invalid XML ; cvc-enumeration-valid: Value 'INVALID_ACTION' is not facet-valid with respect to enumeration '[CREATE, DELETE, UPSERT]'. It must be a value from the enumeration."
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    assert len(response["ResourceRecordSets"]) == 2


@mock_aws
def test_change_resource_record_set_create__should_fail_when_record_already_exists():
    ZONE = "cname.local"
    FQDN = f"test.{ZONE}"
    FQDN_TARGET = "develop.domain.com"

    client = boto3.client("route53", region_name="us-east-1")
    zone_id = client.create_hosted_zone(
        Name=ZONE, CallerReference="ref", DelegationSetId="string"
    )["HostedZone"]["Id"]
    changes = {
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": FQDN,
                    "Type": "CNAME",
                    "TTL": 600,
                    "ResourceRecords": [{"Value": FQDN_TARGET}],
                },
            }
        ]
    }
    client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=changes)

    with pytest.raises(ClientError) as exc:
        client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=changes)

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidChangeBatch"
    assert (
        err["Message"]
        == "Tried to create resource record set [name='test.cname.local.', type='CNAME'] but it already exists"
    )


@mock_aws
def test_change_resource_record_set__should_create_record_when_using_upsert():
    route53_client = boto3.client("route53", region_name="us-east-1")

    hosted_zone = route53_client.create_hosted_zone(
        Name="example.com", CallerReference="irrelevant"
    )["HostedZone"]

    resource_record = {
        "Name": "test.example.com.",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "www.test.example.com"}],
    }

    route53_client.change_resource_record_sets(
        HostedZoneId=hosted_zone["Id"],
        ChangeBatch={
            "Changes": [{"Action": "UPSERT", "ResourceRecordSet": resource_record}],
        },
    )

    response = route53_client.list_resource_record_sets(HostedZoneId=hosted_zone["Id"])

    # The 1st and 2nd records are NS and SOA records, respectively.
    assert len(response["ResourceRecordSets"]) == 3
    assert response["ResourceRecordSets"][2] == resource_record

    # a subsequest UPSERT with the same ChangeBatch should succeed as well
    route53_client.change_resource_record_sets(
        HostedZoneId=hosted_zone["Id"],
        ChangeBatch={
            "Changes": [{"Action": "UPSERT", "ResourceRecordSet": resource_record}],
        },
    )
    response = route53_client.list_resource_record_sets(HostedZoneId=hosted_zone["Id"])

    # The 1st and 2nd records are NS and SOA records, respectively.
    assert len(response["ResourceRecordSets"]) == 3
    assert response["ResourceRecordSets"][2] == resource_record


@mock_aws
def test_list_resource_record_sets_name_type_filters():
    conn = boto3.client("route53", region_name="us-east-1")
    create_hosted_zone_response = conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="db"),
    )
    hosted_zone_id = create_hosted_zone_response["HostedZone"]["Id"]

    def create_resource_record_set(rec_type, rec_name):
        payload = {
            "Comment": f"create {rec_type} record {rec_name}",
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": rec_name,
                        "Type": rec_type,
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.1"}],
                    },
                }
            ],
        }
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=payload
        )

    # record_type, record_name
    all_records = [
        ("A", "a.a.db."),
        ("A", "a.b.db."),
        ("A", "b.b.db."),
        ("CNAME", "b.b.db."),
        ("CNAME", "b.c.db."),
        ("CNAME", "c.c.db."),
    ]
    for record_type, record_name in all_records:
        create_resource_record_set(record_type, record_name)

    start_with = 2
    response = conn.list_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        StartRecordType=all_records[start_with][0],
        StartRecordName=all_records[start_with][1],
    )

    assert response["IsTruncated"] is False

    returned_records = [
        (record["Type"], record["Name"]) for record in response["ResourceRecordSets"]
    ]
    assert len(returned_records) == len(all_records) - start_with
    for desired_record in all_records[start_with:]:
        assert desired_record in returned_records


@mock_aws
def test_get_change():
    conn = boto3.client("route53", region_name="us-east-2")

    change_id = "123456"
    response = conn.get_change(Id=change_id)

    assert response["ChangeInfo"]["Id"] == change_id
    assert response["ChangeInfo"]["Status"] == "INSYNC"


@mock_aws
def test_change_resource_record_sets_records_limit():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    assert len(zones["HostedZones"]) == 1
    assert zones["HostedZones"][0]["Name"] == "db."
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Changes creating exactly 1,000 resource records.
    changes = []
    for ci in range(4):
        resourcerecords = []
        for rri in range(250):
            resourcerecords.append({"Value": f"127.0.0.{rri}"})
        changes.append(
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": f"foo{ci}.db.",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": resourcerecords,
                },
            }
        )
    create_1000_resource_records_payload = {
        "Comment": "Create four records with 250 resource records each",
        "Changes": changes,
    }

    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=create_1000_resource_records_payload
    )

    # Changes creating over 1,000 resource records.
    too_many_changes = create_1000_resource_records_payload["Changes"].copy()
    too_many_changes.append(
        {
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "toomany.db.",
                "Type": "A",
                "TTL": 10,
                "ResourceRecords": [{"Value": "127.0.0.1"}],
            },
        }
    )

    create_1001_resource_records_payload = {
        "Comment": "Create four records with 250 resource records each, plus one more",
        "Changes": too_many_changes,
    }
    with pytest.raises(ClientError) as exc:
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch=create_1001_resource_records_payload,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidChangeBatch"

    # Changes upserting exactly 500 resource records.
    changes = []
    for ci in range(2):
        resourcerecords = []
        for rri in range(250):
            resourcerecords.append({"Value": f"127.0.0.{rri}"})
        changes.append(
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": f"foo{ci}.db.",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": resourcerecords,
                },
            }
        )
    upsert_500_resource_records_payload = {
        "Comment": "Upsert two records with 250 resource records each",
        "Changes": changes,
    }

    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=upsert_500_resource_records_payload
    )

    # Changes upserting over 1,000 resource records.
    too_many_changes = upsert_500_resource_records_payload["Changes"].copy()
    too_many_changes.append(
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "toomany.db.",
                "Type": "A",
                "TTL": 10,
                "ResourceRecords": [{"Value": "127.0.0.1"}],
            },
        }
    )

    upsert_501_resource_records_payload = {
        "Comment": "Upsert two records with 250 resource records each, plus one more",
        "Changes": too_many_changes,
    }

    with pytest.raises(ClientError) as exc:
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=upsert_501_resource_records_payload
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidChangeBatch"
    assert err["Message"] == "Number of records limit of 1000 exceeded."


@mock_aws
def test_list_resource_recordset_pagination():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    assert len(zones["HostedZones"]) == 1
    assert zones["HostedZones"][0]["Name"] == "db."
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create A Record.
    a_record_endpoint_payload = {
        "Comment": "Create 500 A records",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": f"env{idx}.redis.db.",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
            for idx in range(500)
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=a_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(
        HostedZoneId=hosted_zone_id, MaxItems="100"
    )
    assert len(response["ResourceRecordSets"]) == 100
    assert response["IsTruncated"]
    assert response["MaxItems"] == "100"
    assert response["NextRecordName"] == "env187.redis.db."
    assert response["NextRecordType"] == "A"

    response = conn.list_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        StartRecordName=response["NextRecordName"],
        StartRecordType=response["NextRecordType"],
    )
    assert len(response["ResourceRecordSets"]) == 300
    assert response["IsTruncated"] is True
    assert response["MaxItems"] == "300"
    assert response["NextRecordName"] == "env457.redis.db."
    assert response["NextRecordType"] == "A"

    response = conn.list_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        StartRecordName=response["NextRecordName"],
        StartRecordType=response["NextRecordType"],
    )
    assert len(response["ResourceRecordSets"]) == 102
    assert response["IsTruncated"] is False
    assert response["MaxItems"] == "300"
    assert "NextRecordName" not in response
    assert "NextRecordType" not in response


@mock_aws
def test_get_dns_sec():
    client = boto3.client("route53", region_name="us-east-1")

    hosted_zone_id = client.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]["Id"]
    dns_sec = client.get_dnssec(HostedZoneId=hosted_zone_id)
    assert dns_sec["Status"] == {"ServeSignature": "NOT_SIGNING"}


@mock_aws
@pytest.mark.parametrize(
    "domain1,domain2",
    (
        ["a.com", "a.com"],
        ["a.b.com", "b.com"],
        ["b.com", "a.b.com"],
        ["a.b.com", "a.b.com"],
    ),
)
def test_conflicting_domain_exists(domain1, domain2):
    delegation_set_id = "N10015061S366L6NMTRKQ"
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name=domain1,
        CallerReference=str(hash("foo")),
        DelegationSetId=delegation_set_id,
    )
    with pytest.raises(ClientError) as exc_info:
        conn.create_hosted_zone(
            Name=domain2,
            CallerReference=str(hash("bar")),
            DelegationSetId=delegation_set_id,
        )
    assert exc_info.value.response.get("Error").get("Code") == "ConflictingDomainExists"
    for string in [delegation_set_id, domain2]:
        assert string in exc_info.value.response.get("Error").get("Message")

    # Now test that these domains can be created with different delegation set ids
    conn.create_hosted_zone(
        Name=domain1,
        CallerReference=str(hash("foo")),
    )
    conn.create_hosted_zone(
        Name=domain2,
        CallerReference=str(hash("bar")),
    )

    # And, finally, test that these domains can be created with different named delegation sets
    conn.create_hosted_zone(
        Name=domain1,
        CallerReference=str(hash("foo")),
        DelegationSetId="1",
    )
    conn.create_hosted_zone(
        Name=domain2,
        CallerReference=str(hash("bar")),
        DelegationSetId="2",
    )
