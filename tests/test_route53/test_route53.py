from __future__ import unicode_literals

import boto
import boto3
from boto.route53.healthcheck import HealthCheck
from boto.route53.record import ResourceRecordSets

import sure  # noqa

import uuid

import botocore
from nose.tools import assert_raises

from moto import mock_route53, mock_route53_deprecated


@mock_route53_deprecated
def test_hosted_zone():
    conn = boto.connect_route53('the_key', 'the_secret')
    firstzone = conn.create_hosted_zone("testdns.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.create_hosted_zone("testdns1.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(2)

    id1 = firstzone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]
    zone = conn.get_hosted_zone(id1)
    zone["GetHostedZoneResponse"]["HostedZone"][
        "Name"].should.equal("testdns.aws.com.")

    conn.delete_hosted_zone(id1)
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.get_hosted_zone.when.called_with("abcd").should.throw(
        boto.route53.exception.DNSServerError, "404 Not Found")


@mock_route53_deprecated
def test_rrset():
    conn = boto.connect_route53('the_key', 'the_secret')

    conn.get_all_rrsets.when.called_with("abcd", type="A").should.throw(
        boto.route53.exception.DNSServerError, "404 Not Found")

    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]

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

    rrsets = conn.get_all_rrsets(
        zoneid, name="foo.bar.testdns.aws.com", type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('1.2.3.4')

    rrsets = conn.get_all_rrsets(
        zoneid, name="bar.foo.testdns.aws.com", type="A")
    rrsets.should.have.length_of(2)
    resource_records = [rr for rr_set in rrsets for rr in rr_set.resource_records]
    resource_records.should.contain('1.2.3.4')
    resource_records.should.contain('5.6.7.8')

    rrsets = conn.get_all_rrsets(
        zoneid, name="foo.foo.testdns.aws.com", type="A")
    rrsets.should.have.length_of(0)


@mock_route53_deprecated
def test_rrset_with_multiple_values():
    conn = boto.connect_route53('the_key', 'the_secret')
    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    set(rrsets[0].resource_records).should.equal(set(['1.2.3.4', '5.6.7.8']))


@mock_route53_deprecated
def test_alias_rrset():
    conn = boto.connect_route53('the_key', 'the_secret')
    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("CREATE", "foo.alias.testdns.aws.com", "A",
                       alias_hosted_zone_id="Z3DG6IL3SJCGPX", alias_dns_name="foo.testdns.aws.com")
    changes.add_change("CREATE", "bar.alias.testdns.aws.com", "CNAME",
                       alias_hosted_zone_id="Z3DG6IL3SJCGPX", alias_dns_name="bar.testdns.aws.com")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrset_records = [(rr_set.name, rr) for rr_set in rrsets for rr in rr_set.resource_records]
    rrset_records.should.have.length_of(2)
    rrset_records.should.contain(('foo.alias.testdns.aws.com', 'foo.testdns.aws.com'))
    rrset_records.should.contain(('bar.alias.testdns.aws.com', 'bar.testdns.aws.com'))
    rrsets[0].resource_records[0].should.equal('foo.testdns.aws.com')
    rrsets = conn.get_all_rrsets(zoneid, type="CNAME")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('bar.testdns.aws.com')


@mock_route53_deprecated
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

    checks = conn.get_list_health_checks()['ListHealthChecksResponse'][
        'HealthChecks']
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


@mock_route53_deprecated
def test_delete_health_check():
    conn = boto.connect_route53('the_key', 'the_secret')

    check = HealthCheck(
        ip_addr="10.0.0.25",
        port=80,
        hc_type="HTTP",
        resource_path="/",
    )
    conn.create_health_check(check)

    checks = conn.get_list_health_checks()['ListHealthChecksResponse'][
        'HealthChecks']
    list(checks).should.have.length_of(1)
    health_check_id = checks[0]['Id']

    conn.delete_health_check(health_check_id)
    checks = conn.get_list_health_checks()['ListHealthChecksResponse'][
        'HealthChecks']
    list(checks).should.have.length_of(0)


@mock_route53_deprecated
def test_use_health_check_in_resource_record_set():
    conn = boto.connect_route53('the_key', 'the_secret')

    check = HealthCheck(
        ip_addr="10.0.0.25",
        port=80,
        hc_type="HTTP",
        resource_path="/",
    )
    check = conn.create_health_check(
        check)['CreateHealthCheckResponse']['HealthCheck']
    check_id = check['Id']

    zone = conn.create_hosted_zone("testdns.aws.com")
    zone_id = zone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]

    changes = ResourceRecordSets(conn, zone_id)
    change = changes.add_change(
        "CREATE", "foo.bar.testdns.aws.com", "A", health_check=check_id)
    change.add_value("1.2.3.4")
    changes.commit()

    record_sets = conn.get_all_rrsets(zone_id)
    record_sets[0].health_check.should.equal(check_id)


@mock_route53_deprecated
def test_hosted_zone_comment_preserved():
    conn = boto.connect_route53('the_key', 'the_secret')

    firstzone = conn.create_hosted_zone(
        "testdns.aws.com.", comment="test comment")
    zone_id = firstzone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(zone_id)
    hosted_zone["GetHostedZoneResponse"]["HostedZone"][
        "Config"]["Comment"].should.equal("test comment")

    hosted_zones = conn.get_all_hosted_zones()
    hosted_zones["ListHostedZonesResponse"]["HostedZones"][
        0]["Config"]["Comment"].should.equal("test comment")

    zone = conn.get_zone("testdns.aws.com.")
    zone.config["Comment"].should.equal("test comment")


@mock_route53_deprecated
def test_deleting_weighted_route():
    conn = boto.connect_route53()

    conn.create_hosted_zone("testdns.aws.com.")
    zone = conn.get_zone("testdns.aws.com.")

    zone.add_cname("cname.testdns.aws.com", "example.com",
                   identifier=('success-test-foo', '50'))
    zone.add_cname("cname.testdns.aws.com", "example.com",
                   identifier=('success-test-bar', '50'))

    cnames = zone.get_cname('cname.testdns.aws.com.', all=True)
    cnames.should.have.length_of(2)
    foo_cname = [cname for cname in cnames if cname.identifier ==
                 'success-test-foo'][0]

    zone.delete_record(foo_cname)
    cname = zone.get_cname('cname.testdns.aws.com.', all=True)
    # When get_cname only had one result, it returns just that result instead
    # of a list.
    cname.identifier.should.equal('success-test-bar')


@mock_route53_deprecated
def test_deleting_latency_route():
    conn = boto.connect_route53()

    conn.create_hosted_zone("testdns.aws.com.")
    zone = conn.get_zone("testdns.aws.com.")

    zone.add_cname("cname.testdns.aws.com", "example.com",
                   identifier=('success-test-foo', 'us-west-2'))
    zone.add_cname("cname.testdns.aws.com", "example.com",
                   identifier=('success-test-bar', 'us-west-1'))

    cnames = zone.get_cname('cname.testdns.aws.com.', all=True)
    cnames.should.have.length_of(2)
    foo_cname = [cname for cname in cnames if cname.identifier ==
                 'success-test-foo'][0]
    foo_cname.region.should.equal('us-west-2')

    zone.delete_record(foo_cname)
    cname = zone.get_cname('cname.testdns.aws.com.', all=True)
    # When get_cname only had one result, it returns just that result instead
    # of a list.
    cname.identifier.should.equal('success-test-bar')
    cname.region.should.equal('us-west-1')


@mock_route53_deprecated
def test_hosted_zone_private_zone_preserved():
    conn = boto.connect_route53('the_key', 'the_secret')

    firstzone = conn.create_hosted_zone(
        "testdns.aws.com.", private_zone=True, vpc_id='vpc-fake', vpc_region='us-east-1')
    zone_id = firstzone["CreateHostedZoneResponse"][
        "HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(zone_id)
    # in (original) boto, these bools returned as strings.
    hosted_zone["GetHostedZoneResponse"]["HostedZone"][
        "Config"]["PrivateZone"].should.equal('True')

    hosted_zones = conn.get_all_hosted_zones()
    hosted_zones["ListHostedZonesResponse"]["HostedZones"][
        0]["Config"]["PrivateZone"].should.equal('True')

    zone = conn.get_zone("testdns.aws.com.")
    zone.config["PrivateZone"].should.equal('True')


@mock_route53
def test_hosted_zone_private_zone_preserved_boto3():
    conn = boto3.client('route53', region_name='us-east-1')
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

    hosted_zones = conn.list_hosted_zones_by_name(DNSName="testdns.aws.com.")
    len(hosted_zones["HostedZones"]).should.equal(1)
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)


@mock_route53
def test_list_or_change_tags_for_resource_request():
    conn = boto3.client('route53', region_name='us-east-1')
    health_check = conn.create_health_check(
        CallerReference='foobar',
        HealthCheckConfig={
            'IPAddress': '192.0.2.44',
            'Port': 123,
            'Type': 'HTTP',
            'ResourcePath': '/',
            'RequestInterval': 30,
            'FailureThreshold': 123,
            'HealthThreshold': 123,
        }
    )
    healthcheck_id = health_check['HealthCheck']['Id']

    tag1 = {"Key": "Deploy", "Value": "True"}
    tag2 = {"Key": "Name", "Value": "UnitTest"}

    # Test adding a tag for a resource id
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        AddTags=[tag1, tag2]
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(
        ResourceType='healthcheck', ResourceId=healthcheck_id)
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
    response = conn.list_tags_for_resource(
        ResourceType='healthcheck', ResourceId=healthcheck_id)
    response.should.contain('ResourceTagSet')
    response['ResourceTagSet']['Tags'].should_not.contain(tag1)
    response['ResourceTagSet']['Tags'].should.contain(tag2)

    # Remove the second tag
    conn.change_tags_for_resource(
        ResourceType='healthcheck',
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag2['Key']]
    )

    response = conn.list_tags_for_resource(
        ResourceType='healthcheck', ResourceId=healthcheck_id)
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

    response = conn.list_tags_for_resource(
        ResourceType='healthcheck', ResourceId=healthcheck_id)
    response['ResourceTagSet']['Tags'].should.be.empty


@mock_route53
def test_list_hosted_zones_by_name():
    conn = boto3.client('route53', region_name='us-east-1')
    conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash('foo')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="test com",
        )
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash('bar')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="test org",
        )
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash('bar')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="test org 2",
        )
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
    conn = boto3.client('route53', region_name='us-east-1')
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash('foo')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="db",
        )
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create A Record.
    a_record_endpoint_payload = {
        'Comment': 'create A record prod.redis.db',
        'Changes': [
            {
                'Action': 'CREATE',
                'ResourceRecordSet': {
                    'Name': 'prod.redis.db',
                    'Type': 'A',
                    'TTL': 10,
                    'ResourceRecords': [{
                        'Value': '127.0.0.1'
                    }]
                }
            }
        ]
    }
    conn.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=a_record_endpoint_payload)

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response['ResourceRecordSets']).should.equal(1)
    a_record_detail = response['ResourceRecordSets'][0]
    a_record_detail['Name'].should.equal('prod.redis.db')
    a_record_detail['Type'].should.equal('A')
    a_record_detail['TTL'].should.equal(10)
    a_record_detail['ResourceRecords'].should.equal([{'Value': '127.0.0.1'}])

    # Update type to CNAME
    cname_record_endpoint_payload = {
        'Comment': 'Update to CNAME prod.redis.db',
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'prod.redis.db',
                    'Type': 'CNAME',
                    'TTL': 60,
                    'ResourceRecords': [{
                        'Value': '192.168.1.1'
                    }]
                }
            }
        ]
    }
    conn.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=cname_record_endpoint_payload)

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response['ResourceRecordSets']).should.equal(1)
    cname_record_detail = response['ResourceRecordSets'][0]
    cname_record_detail['Name'].should.equal('prod.redis.db')
    cname_record_detail['Type'].should.equal('CNAME')
    cname_record_detail['TTL'].should.equal(60)
    cname_record_detail['ResourceRecords'].should.equal([{'Value': '192.168.1.1'}])

    # Delete record.
    delete_payload = {
        'Comment': 'delete prod.redis.db',
        'Changes': [
            {
                'Action': 'DELETE',
                'ResourceRecordSet': {
                    'Name': 'prod.redis.db',
                    'Type': 'CNAME',
                }
            }
        ]
    }
    conn.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload)
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response['ResourceRecordSets']).should.equal(0)


@mock_route53
def test_change_resource_record_invalid():
    conn = boto3.client('route53', region_name='us-east-1')
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash('foo')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="db",
        )
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    invalid_a_record_payload = {
        'Comment': 'this should fail',
        'Changes': [
            {
                'Action': 'CREATE',
                'ResourceRecordSet': {
                    'Name': 'prod.scooby.doo',
                    'Type': 'A',
                    'TTL': 10,
                    'ResourceRecords': [{
                        'Value': '127.0.0.1'
                    }]
                }
            }
        ]
    }

    with assert_raises(botocore.exceptions.ClientError):
        conn.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=invalid_a_record_payload)

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response['ResourceRecordSets']).should.equal(0)

    invalid_cname_record_payload = {
        'Comment': 'this should also fail',
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'prod.scooby.doo',
                    'Type': 'CNAME',
                    'TTL': 10,
                    'ResourceRecords': [{
                        'Value': '127.0.0.1'
                    }]
                }
            }
        ]
    }

    with assert_raises(botocore.exceptions.ClientError):
        conn.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=invalid_cname_record_payload)

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response['ResourceRecordSets']).should.equal(0)


@mock_route53
def test_list_resource_record_sets_name_type_filters():
    conn = boto3.client('route53', region_name='us-east-1')
    create_hosted_zone_response = conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash('foo')),
        HostedZoneConfig=dict(
            PrivateZone=True,
            Comment="db",
        )
    )
    hosted_zone_id = create_hosted_zone_response['HostedZone']['Id']

    def create_resource_record_set(rec_type, rec_name):
        payload = {
            'Comment': 'create {} record {}'.format(rec_type, rec_name),
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': rec_name,
                        'Type': rec_type,
                        'TTL': 10,
                        'ResourceRecords': [{
                            'Value': '127.0.0.1'
                        }]
                    }
                }
            ]
        }
        conn.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=payload)

    # record_type, record_name
    all_records = [
        ('A', 'a.a.db'),
        ('A', 'a.b.db'),
        ('A', 'b.b.db'),
        ('CNAME', 'b.b.db'),
        ('CNAME', 'b.c.db'),
        ('CNAME', 'c.c.db')
    ]
    for record_type, record_name in all_records:
        create_resource_record_set(record_type, record_name)

    start_with = 2
    response = conn.list_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        StartRecordType=all_records[start_with][0],
        StartRecordName=all_records[start_with][1]
    )

    returned_records = [(record['Type'], record['Name']) for record in response['ResourceRecordSets']]
    len(returned_records).should.equal(len(all_records) - start_with)
    for desired_record in all_records[start_with:]:
        returned_records.should.contain(desired_record)
