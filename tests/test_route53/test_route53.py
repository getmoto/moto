from __future__ import unicode_literals
import urllib2

import boto
from boto.exception import S3ResponseError
from boto.s3.key import Key
from boto.route53.record import ResourceRecordSets
from freezegun import freeze_time
import requests

import sure  # noqa

from moto import mock_route53


@mock_route53
def test_hosted_zone():
    conn = boto.connect_route53('the_key', 'the_secret')
    firstzone = conn.create_hosted_zone("testdns.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    secondzone = conn.create_hosted_zone("testdns1.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(2)

    id1 = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"]
    zone = conn.get_hosted_zone(id1)
    zone["GetHostedZoneResponse"]["HostedZone"]["Name"].should.equal("testdns.aws.com")

    conn.delete_hosted_zone(id1)
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.get_hosted_zone.when.called_with("abcd").should.throw(boto.route53.exception.DNSServerError, "404 Not Found")


@mock_route53
def test_rrset():
    conn = boto.connect_route53('the_key', 'the_secret')

    conn.get_all_rrsets.when.called_with("abcd", type="A").\
                should.throw(boto.route53.exception.DNSServerError, "404 Not Found")

    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"]

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
