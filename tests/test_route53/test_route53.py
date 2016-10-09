from __future__ import unicode_literals

import boto
import boto3
from boto.route53.healthcheck import HealthCheck
from boto.route53.record import ResourceRecordSets

import sure  # noqa

import uuid

from moto import mock_route53


@mock_route53
def test_hosted_zone():
    conn = boto.connect_route53('the_key', 'the_secret')
    firstzone = conn.create_hosted_zone("testdns.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.create_hosted_zone("testdns1.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(2)

    id1 = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]
    zone = conn.get_hosted_zone(id1)
    zone["GetHostedZoneResponse"]["HostedZone"]["Name"].should.equal("testdns.aws.com")

    conn.delete_hosted_zone(id1)
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.get_hosted_zone.when.called_with("abcd").should.throw(boto.route53.exception.DNSServerError, "404 Not Found")


@mock_route53
def test_rrset():
    conn = boto.connect_route53('the_key', 'the_secret')

    conn.get_all_rrsets.when.called_with("abcd", type="A").should.throw(
        boto.route53.exception.DNSServerError, "404 Not Found")

    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('1.2.3.4')

    rrsets = conn.get_all_rrsets(zoneid, type="CNAME")
    rrsets.should.have.length_of(0)

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('5.6.7.8')

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
    rrsets[0].resource_records[0].should.equal('1.2.3.4')

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("UPSERT", "foo.bar.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('5.6.7.8')

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    changes.commit()

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    change = changes.add_change("CREATE", "bar.foo.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(2)

    rrsets = conn.get_all_rrsets(zoneid, name="foo.bar.testdns.aws.com", type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('1.2.3.4')

    rrsets = conn.get_all_rrsets(zoneid, name="bar.foo.testdns.aws.com", type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('5.6.7.8')

    rrsets = conn.get_all_rrsets(zoneid, name="foo.foo.testdns.aws.com", type="A")
    rrsets.should.have.length_of(0)


@mock_route53
def test_rrset_with_multiple_values():
    conn = boto.connect_route53('the_key', 'the_secret')
    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    set(rrsets[0].resource_records).should.equal(set(['1.2.3.4', '5.6.7.8']))


@mock_route53
def test_alias_rrset():
    conn = boto.connect_route53('the_key', 'the_secret')
    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("CREATE", "foo.alias.testdns.aws.com", "A", alias_hosted_zone_id="Z3DG6IL3SJCGPX", alias_dns_name="foo.testdns.aws.com")
    changes.add_change("CREATE", "bar.alias.testdns.aws.com", "CNAME", alias_hosted_zone_id="Z3DG6IL3SJCGPX", alias_dns_name="bar.testdns.aws.com")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('foo.testdns.aws.com')
    rrsets = conn.get_all_rrsets(zoneid, type="CNAME")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('bar.testdns.aws.com')


@mock_route53
def test_create_health_check():
    conn = boto.connect_route53('the_key', 'the_secret')

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

    checks = conn.get_list_health_checks()['ListHealthChecksResponse']['HealthChecks']
    list(checks).should.have.length_of(1)
    check = checks[0]
    config = check['HealthCheckConfig']
    config['IPAddress'].should.equal("10.0.0.25")
    config['Port'].should.equal("80")
    config['Type'].should.equal("HTTP")
    config['ResourcePath'].should.equal("/")
    config['FullyQualifiedDomainName'].should.equal("example.com")
    config['SearchString'].should.equal("a good response")
    config['RequestInterval'].should.equal("10")
    config['FailureThreshold'].should.equal("2")


@mock_route53
def test_delete_health_check():
    conn = boto.connect_route53('the_key', 'the_secret')

    check = HealthCheck(
        ip_addr="10.0.0.25",
        port=80,
        hc_type="HTTP",
        resource_path="/",
    )
    conn.create_health_check(check)

    checks = conn.get_list_health_checks()['ListHealthChecksResponse']['HealthChecks']
    list(checks).should.have.length_of(1)
    health_check_id = checks[0]['Id']

    conn.delete_health_check(health_check_id)
    checks = conn.get_list_health_checks()['ListHealthChecksResponse']['HealthChecks']
    list(checks).should.have.length_of(0)


@mock_route53
def test_use_health_check_in_resource_record_set():
    conn = boto.connect_route53('the_key', 'the_secret')

    check = HealthCheck(
        ip_addr="10.0.0.25",
        port=80,
        hc_type="HTTP",
        resource_path="/",
    )
    check = conn.create_health_check(check)['CreateHealthCheckResponse']['HealthCheck']
    check_id = check['Id']

    zone = conn.create_hosted_zone("testdns.aws.com")
    zone_id = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zone_id)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A", health_check=check_id)
    change.add_value("1.2.3.4")
    changes.commit()

    record_sets = conn.get_all_rrsets(zone_id)
    record_sets[0].health_check.should.equal(check_id)


@mock_route53
def test_hosted_zone_comment_preserved():
    conn = boto.connect_route53('the_key', 'the_secret')

    firstzone = conn.create_hosted_zone("testdns.aws.com.", comment="test comment")
    zone_id = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(zone_id)
    hosted_zone["GetHostedZoneResponse"]["HostedZone"]["Config"]["Comment"].should.equal("test comment")

    hosted_zones = conn.get_all_hosted_zones()
    hosted_zones["ListHostedZonesResponse"]["HostedZones"][0]["Config"]["Comment"].should.equal("test comment")

    zone = conn.get_zone("testdns.aws.com.")
    zone.config["Comment"].should.equal("test comment")


@mock_route53
def test_deleting_weighted_route():
    conn = boto.connect_route53()

    conn.create_hosted_zone("testdns.aws.com.")
    zone = conn.get_zone("testdns.aws.com.")

    zone.add_cname("cname.testdns.aws.com", "example.com", identifier=('success-test-foo', '50'))
    zone.add_cname("cname.testdns.aws.com", "example.com", identifier=('success-test-bar', '50'))

    cnames = zone.get_cname('cname.testdns.aws.com.', all=True)
    cnames.should.have.length_of(2)
    foo_cname = [cname for cname in cnames if cname.identifier == 'success-test-foo'][0]

    zone.delete_record(foo_cname)
    cname = zone.get_cname('cname.testdns.aws.com.', all=True)
    # When get_cname only had one result, it returns just that result instead of a list.
    cname.identifier.should.equal('success-test-bar')


@mock_route53
def test_deleting_latency_route():
    conn = boto.connect_route53()

    conn.create_hosted_zone("testdns.aws.com.")
    zone = conn.get_zone("testdns.aws.com.")

    zone.add_cname("cname.testdns.aws.com", "example.com", identifier=('success-test-foo', 'us-west-2'))
    zone.add_cname("cname.testdns.aws.com", "example.com", identifier=('success-test-bar', 'us-west-1'))

    cnames = zone.get_cname('cname.testdns.aws.com.', all=True)
    cnames.should.have.length_of(2)
    foo_cname = [cname for cname in cnames if cname.identifier == 'success-test-foo'][0]
    foo_cname.region.should.equal('us-west-2')

    zone.delete_record(foo_cname)
    cname = zone.get_cname('cname.testdns.aws.com.', all=True)
    # When get_cname only had one result, it returns just that result instead of a list.
    cname.identifier.should.equal('success-test-bar')
    cname.region.should.equal('us-west-1')


@mock_route53
def test_hosted_zone_private_zone_preserved():
    conn = boto.connect_route53('the_key', 'the_secret')

    firstzone = conn.create_hosted_zone("testdns.aws.com.", private_zone=True, vpc_id='vpc-fake', vpc_region='us-east-1')
    zone_id = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(zone_id)
    # in (original) boto, these bools returned as strings.
    hosted_zone["GetHostedZoneResponse"]["HostedZone"]["Config"]["PrivateZone"].should.equal('True')

    hosted_zones = conn.get_all_hosted_zones()
    hosted_zones["ListHostedZonesResponse"]["HostedZones"][0]["Config"]["PrivateZone"].should.equal('True')

    zone = conn.get_zone("testdns.aws.com.")
    zone.config["PrivateZone"].should.equal('True')


@mock_route53
def test_hosted_zone_private_zone_preserved_boto3():
    conn = boto3.client('route53')
    # TODO: actually create_hosted_zone statements with PrivateZone=True, but without
    # a _valid_ vpc-id should fail.
    firstzone = conn.create_hosted_zone(
        Name="testdns.aws.com.",
        CallerReference=str(hash('foo')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="Test",
        )
    )

    zone_id = firstzone["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    hosted_zone["HostedZone"]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones()
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)

    # zone = conn.list_hosted_zones_by_name(DNSName="testdns.aws.com.")
    # zone.config["PrivateZone"].should.equal(True)

@mock_route53
def test_list_or_change_tags_for_resource_request():
    conn = boto3.client('route53')
    healthcheck_id = str(uuid.uuid4())

    tag1 = {"Key": "Deploy", "Value": "True"}
    tag2 = {"Key": "Name", "Value": "UnitTest"}

    # Test adding a tag for a resource id
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        AddTags=[tag1, tag2]
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(ResourceType='healthcheck', ResourceId=healthcheck_id)
    response.should.contain('ResourceTagSet')

    # Validate that each key was added
    response['ResourceTagSet']['Tags'].should.contain(tag1)
    response['ResourceTagSet']['Tags'].should.contain(tag2)

    len(response['ResourceTagSet']['Tags']).should.equal(2)

    # Try to remove the tags
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag1['Key']]
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(ResourceType='healthcheck', ResourceId=healthcheck_id)
    response.should.contain('ResourceTagSet')
    response['ResourceTagSet']['Tags'].should_not.contain(tag1)
    response['ResourceTagSet']['Tags'].should.contain(tag2)

    # Remove the second tag
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag2['Key']]
    )

    response = conn.list_tags_for_resource(ResourceType='healthcheck', ResourceId=healthcheck_id)
    response['ResourceTagSet']['Tags'].should_not.contain(tag2)

    # Re-add the tags
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        AddTags=[tag1, tag2]
    )

    # Remove both
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag1['Key'], tag2['Key']]
    )

    response = conn.list_tags_for_resource(ResourceType='healthcheck', ResourceId=healthcheck_id)
    response['ResourceTagSet']['Tags'].should.be.empty
