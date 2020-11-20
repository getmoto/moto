from __future__ import unicode_literals

import boto
import boto3
from boto.route53.healthcheck import HealthCheck
from boto.route53.record import ResourceRecordSets

import sure  # noqa

import uuid

import botocore
import pytest

from moto import mock_route53, mock_route53_deprecated


@mock_route53_deprecated
def test_hosted_zone():
    conn = boto.connect_route53("the_key", "the_secret")
    firstzone = conn.create_hosted_zone("testdns.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.create_hosted_zone("testdns1.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(2)

    id1 = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]
    zone = conn.get_hosted_zone(id1)
    zone["GetHostedZoneResponse"]["HostedZone"]["Name"].should.equal("testdns.aws.com.")

    conn.delete_hosted_zone(id1)
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.get_hosted_zone.when.called_with("abcd").should.throw(
        boto.route53.exception.DNSServerError, "404 Not Found"
    )


@mock_route53_deprecated
def test_rrset():
    conn = boto.connect_route53("the_key", "the_secret")

    conn.get_all_rrsets.when.called_with("abcd", type="A").should.throw(
        boto.route53.exception.DNSServerError, "404 Not Found"
    )

    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal("1.2.3.4")

    rrsets = conn.get_all_rrsets(zoneid, type="CNAME")
    rrsets.should.have.length_of(0)

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal("5.6.7.8")

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid)
    rrsets.should.have.length_of(0)

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("UPSERT", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal("1.2.3.4")

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("UPSERT", "foo.bar.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal("5.6.7.8")

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("UPSERT", "foo.bar.testdns.aws.com", "TXT")
    change.add_value("foo")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid)
    rrsets.should.have.length_of(2)
    rrsets[0].resource_records[0].should.equal("5.6.7.8")
    rrsets[1].resource_records[0].should.equal("foo")

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "TXT")
    changes.commit()

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    change = changes.add_change("CREATE", "bar.foo.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(2)

    rrsets = conn.get_all_rrsets(zoneid, name="bar.foo.testdns.aws.com", type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal("5.6.7.8")

    rrsets = conn.get_all_rrsets(zoneid, name="foo.bar.testdns.aws.com", type="A")
    rrsets.should.have.length_of(2)
    resource_records = [rr for rr_set in rrsets for rr in rr_set.resource_records]
    resource_records.should.contain("1.2.3.4")
    resource_records.should.contain("5.6.7.8")

    rrsets = conn.get_all_rrsets(zoneid, name="foo.foo.testdns.aws.com", type="A")
    rrsets.should.have.length_of(0)


@mock_route53_deprecated
def test_rrset_with_multiple_values():
    conn = boto.connect_route53("the_key", "the_secret")
    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    set(rrsets[0].resource_records).should.equal(set(["1.2.3.4", "5.6.7.8"]))


@mock_route53_deprecated
def test_alias_rrset():
    conn = boto.connect_route53("the_key", "the_secret")
    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change(
        "CREATE",
        "foo.alias.testdns.aws.com",
        "A",
        alias_hosted_zone_id="Z3DG6IL3SJCGPX",
        alias_dns_name="foo.testdns.aws.com",
    )
    changes.add_change(
        "CREATE",
        "bar.alias.testdns.aws.com",
        "CNAME",
        alias_hosted_zone_id="Z3DG6IL3SJCGPX",
        alias_dns_name="bar.testdns.aws.com",
    )
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    alias_targets = [rr_set.alias_dns_name for rr_set in rrsets]
    alias_targets.should.have.length_of(2)
    alias_targets.should.contain("foo.testdns.aws.com")
    alias_targets.should.contain("bar.testdns.aws.com")
    rrsets[0].alias_dns_name.should.equal("foo.testdns.aws.com")
    rrsets[0].resource_records.should.have.length_of(0)
    rrsets = conn.get_all_rrsets(zoneid, type="CNAME")
    rrsets.should.have.length_of(1)
    rrsets[0].alias_dns_name.should.equal("bar.testdns.aws.com")
    rrsets[0].resource_records.should.have.length_of(0)


@mock_route53_deprecated
def test_create_health_check():
    conn = boto.connect_route53("the_key", "the_secret")

    check = HealthCheck(
        ip_addr="10.0.0.25",
        port=80,
        hc_type="HTTP",
        resource_path="/",
        fqdn="example.com",
        string_match="a good response",
        request_interval=10,
        failure_threshold=2,
    )
    conn.create_health_check(check)

    checks = conn.get_list_health_checks()["ListHealthChecksResponse"]["HealthChecks"]
    list(checks).should.have.length_of(1)
    check = checks[0]
    config = check["HealthCheckConfig"]
    config["IPAddress"].should.equal("10.0.0.25")
    config["Port"].should.equal("80")
    config["Type"].should.equal("HTTP")
    config["ResourcePath"].should.equal("/")
    config["FullyQualifiedDomainName"].should.equal("example.com")
    config["SearchString"].should.equal("a good response")
    config["RequestInterval"].should.equal("10")
    config["FailureThreshold"].should.equal("2")


@mock_route53_deprecated
def test_delete_health_check():
    conn = boto.connect_route53("the_key", "the_secret")

    check = HealthCheck(ip_addr="10.0.0.25", port=80, hc_type="HTTP", resource_path="/")
    conn.create_health_check(check)

    checks = conn.get_list_health_checks()["ListHealthChecksResponse"]["HealthChecks"]
    list(checks).should.have.length_of(1)
    health_check_id = checks[0]["Id"]

    conn.delete_health_check(health_check_id)
    checks = conn.get_list_health_checks()["ListHealthChecksResponse"]["HealthChecks"]
    list(checks).should.have.length_of(0)


@mock_route53_deprecated
def test_use_health_check_in_resource_record_set():
    conn = boto.connect_route53("the_key", "the_secret")

    check = HealthCheck(ip_addr="10.0.0.25", port=80, hc_type="HTTP", resource_path="/")
    check = conn.create_health_check(check)["CreateHealthCheckResponse"]["HealthCheck"]
    check_id = check["Id"]

    zone = conn.create_hosted_zone("testdns.aws.com")
    zone_id = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zone_id)
    change = changes.add_change(
        "CREATE", "foo.bar.testdns.aws.com", "A", health_check=check_id
    )
    change.add_value("1.2.3.4")
    changes.commit()

    record_sets = conn.get_all_rrsets(zone_id)
    record_sets[0].health_check.should.equal(check_id)


@mock_route53_deprecated
def test_hosted_zone_comment_preserved():
    conn = boto.connect_route53("the_key", "the_secret")

    firstzone = conn.create_hosted_zone("testdns.aws.com.", comment="test comment")
    zone_id = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(zone_id)
    hosted_zone["GetHostedZoneResponse"]["HostedZone"]["Config"][
        "Comment"
    ].should.equal("test comment")

    hosted_zones = conn.get_all_hosted_zones()
    hosted_zones["ListHostedZonesResponse"]["HostedZones"][0]["Config"][
        "Comment"
    ].should.equal("test comment")

    zone = conn.get_zone("testdns.aws.com.")
    zone.config["Comment"].should.equal("test comment")


@mock_route53_deprecated
def test_deleting_weighted_route():
    conn = boto.connect_route53()

    conn.create_hosted_zone("testdns.aws.com.")
    zone = conn.get_zone("testdns.aws.com.")

    zone.add_cname(
        "cname.testdns.aws.com", "example.com", identifier=("success-test-foo", "50")
    )
    zone.add_cname(
        "cname.testdns.aws.com", "example.com", identifier=("success-test-bar", "50")
    )

    cnames = zone.get_cname("cname.testdns.aws.com.", all=True)
    cnames.should.have.length_of(2)
    foo_cname = [cname for cname in cnames if cname.identifier == "success-test-foo"][0]

    zone.delete_record(foo_cname)
    cname = zone.get_cname("cname.testdns.aws.com.", all=True)
    # When get_cname only had one result, it returns just that result instead
    # of a list.
    cname.identifier.should.equal("success-test-bar")


@mock_route53_deprecated
def test_deleting_latency_route():
    conn = boto.connect_route53()

    conn.create_hosted_zone("testdns.aws.com.")
    zone = conn.get_zone("testdns.aws.com.")

    zone.add_cname(
        "cname.testdns.aws.com",
        "example.com",
        identifier=("success-test-foo", "us-west-2"),
    )
    zone.add_cname(
        "cname.testdns.aws.com",
        "example.com",
        identifier=("success-test-bar", "us-west-1"),
    )

    cnames = zone.get_cname("cname.testdns.aws.com.", all=True)
    cnames.should.have.length_of(2)
    foo_cname = [cname for cname in cnames if cname.identifier == "success-test-foo"][0]
    foo_cname.region.should.equal("us-west-2")

    zone.delete_record(foo_cname)
    cname = zone.get_cname("cname.testdns.aws.com.", all=True)
    # When get_cname only had one result, it returns just that result instead
    # of a list.
    cname.identifier.should.equal("success-test-bar")
    cname.region.should.equal("us-west-1")


@mock_route53_deprecated
def test_hosted_zone_private_zone_preserved():
    conn = boto.connect_route53("the_key", "the_secret")

    firstzone = conn.create_hosted_zone(
        "testdns.aws.com.", private_zone=True, vpc_id="vpc-fake", vpc_region="us-east-1"
    )
    zone_id = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(zone_id)
    # in (original) boto, these bools returned as strings.
    hosted_zone["GetHostedZoneResponse"]["HostedZone"]["Config"][
        "PrivateZone"
    ].should.equal("True")

    hosted_zones = conn.get_all_hosted_zones()
    hosted_zones["ListHostedZonesResponse"]["HostedZones"][0]["Config"][
        "PrivateZone"
    ].should.equal("True")

    zone = conn.get_zone("testdns.aws.com.")
    zone.config["PrivateZone"].should.equal("True")


@mock_route53
def test_hosted_zone_private_zone_preserved_boto3():
    conn = boto3.client("route53", region_name="us-east-1")
    # TODO: actually create_hosted_zone statements with PrivateZone=True, but without
    # a _valid_ vpc-id should fail.
    firstzone = conn.create_hosted_zone(
        Name="testdns.aws.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="Test"),
    )

    zone_id = firstzone["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    hosted_zone["HostedZone"]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones()
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones_by_name(DNSName="testdns.aws.com.")
    len(hosted_zones["HostedZones"]).should.equal(1)
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)


@mock_route53
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
    response["ResourceTagSet"]["Tags"].should.be.empty

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
    response.should.contain("ResourceTagSet")

    # Validate that each key was added
    response["ResourceTagSet"]["Tags"].should.contain(tag1)
    response["ResourceTagSet"]["Tags"].should.contain(tag2)

    len(response["ResourceTagSet"]["Tags"]).should.equal(2)

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
    response.should.contain("ResourceTagSet")
    response["ResourceTagSet"]["Tags"].should_not.contain(tag1)
    response["ResourceTagSet"]["Tags"].should.contain(tag2)

    # Remove the second tag
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag2["Key"]],
    )

    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    response["ResourceTagSet"]["Tags"].should_not.contain(tag2)

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
    response["ResourceTagSet"]["Tags"].should.be.empty


@mock_route53
def test_list_hosted_zones_by_name():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test com"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test org"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test org 2"),
    )

    # test lookup
    zones = conn.list_hosted_zones_by_name(DNSName="test.b.com.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("test.b.com.")
    zones = conn.list_hosted_zones_by_name(DNSName="test.a.org.")
    len(zones["HostedZones"]).should.equal(2)
    zones["HostedZones"][0]["Name"].should.equal("test.a.org.")
    zones["HostedZones"][1]["Name"].should.equal("test.a.org.")

    # test sort order
    zones = conn.list_hosted_zones_by_name()
    len(zones["HostedZones"]).should.equal(3)
    zones["HostedZones"][0]["Name"].should.equal("test.b.com.")
    zones["HostedZones"][1]["Name"].should.equal("test.a.org.")
    zones["HostedZones"][2]["Name"].should.equal("test.a.org.")


@mock_route53
def test_change_resource_record_sets_crud_valid():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
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
    len(response["ResourceRecordSets"]).should.equal(1)
    a_record_detail = response["ResourceRecordSets"][0]
    a_record_detail["Name"].should.equal("prod.redis.db.")
    a_record_detail["Type"].should.equal("A")
    a_record_detail["TTL"].should.equal(10)
    a_record_detail["ResourceRecords"].should.equal([{"Value": "127.0.0.1"}])

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
    len(response["ResourceRecordSets"]).should.equal(1)
    cname_record_detail = response["ResourceRecordSets"][0]
    cname_record_detail["Name"].should.equal("prod.redis.db.")
    cname_record_detail["Type"].should.equal("A")
    cname_record_detail["TTL"].should.equal(60)
    cname_record_detail["ResourceRecords"].should.equal([{"Value": "192.168.1.1"}])

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
    cname_alias_record_detail = response["ResourceRecordSets"][0]
    cname_alias_record_detail["Name"].should.equal("prod.redis.db.")
    cname_alias_record_detail["Type"].should.equal("A")
    cname_alias_record_detail["TTL"].should.equal(60)
    cname_alias_record_detail["AliasTarget"].should.equal(
        {
            "HostedZoneId": hosted_zone_id,
            "DNSName": "prod.redis.alias.",
            "EvaluateTargetHealth": False,
        }
    )
    cname_alias_record_detail.should_not.contain("ResourceRecords")

    # Delete record with wrong type.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {"Name": "prod.redis.db", "Type": "CNAME"},
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)

    # Delete record.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {"Name": "prod.redis.db", "Type": "A"},
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(0)


@mock_route53
def test_change_resource_record_sets_crud_valid_with_special_xml_chars():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
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
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=txt_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)
    a_record_detail = response["ResourceRecordSets"][0]
    a_record_detail["Name"].should.equal("prod.redis.db.")
    a_record_detail["Type"].should.equal("TXT")
    a_record_detail["TTL"].should.equal(10)
    a_record_detail["ResourceRecords"].should.equal([{"Value": "SomeInitialValue"}])

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
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch=txt_record_with_special_char_endpoint_payload,
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)
    cname_record_detail = response["ResourceRecordSets"][0]
    cname_record_detail["Name"].should.equal("prod.redis.db.")
    cname_record_detail["Type"].should.equal("TXT")
    cname_record_detail["TTL"].should.equal(60)
    cname_record_detail["ResourceRecords"].should.equal(
        [{"Value": "SomeInitialValue&NewValue"}]
    )

    # Delete record.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {"Name": "prod.redis.db", "Type": "TXT"},
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(0)


@mock_route53
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

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    record = response["ResourceRecordSets"][0]
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

    record = response["ResourceRecordSets"][1]
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
        if record["SetIdentifier"] == "test1":
            record["Weight"].should.equal(90)
        if record["SetIdentifier"] == "test2":
            record["Weight"].should.equal(10)


@mock_route53
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
    record = response["ResourceRecordSets"][0]
    record["Failover"].should.equal("PRIMARY")


@mock_route53
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
    rrs[0]["GeoLocation"].should.equal({"ContinentCode": "EU"})
    rrs[1]["GeoLocation"].should.equal({"CountryCode": "US", "SubdivisionCode": "NY"})


@mock_route53
def test_change_resource_record_invalid():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
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
    len(response["ResourceRecordSets"]).should.equal(0)

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
    len(response["ResourceRecordSets"]).should.equal(0)


@mock_route53
def test_list_resource_record_sets_name_type_filters():
    conn = boto3.client("route53", region_name="us-east-1")
    create_hosted_zone_response = conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )
    hosted_zone_id = create_hosted_zone_response["HostedZone"]["Id"]

    def create_resource_record_set(rec_type, rec_name):
        payload = {
            "Comment": "create {} record {}".format(rec_type, rec_name),
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

    response["IsTruncated"].should.equal(False)

    returned_records = [
        (record["Type"], record["Name"]) for record in response["ResourceRecordSets"]
    ]
    len(returned_records).should.equal(len(all_records) - start_with)
    for desired_record in all_records[start_with:]:
        returned_records.should.contain(desired_record)


@mock_route53
def test_get_change():
    conn = boto3.client("route53", region_name="us-east-2")

    change_id = "123456"
    response = conn.get_change(Id=change_id)

    response["ChangeInfo"]["Id"].should.equal(change_id)
    response["ChangeInfo"]["Status"].should.equal("INSYNC")
