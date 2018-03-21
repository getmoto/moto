from __future__ import unicode_literals
import os
from sure import expect
from moto.s3.utils import bucket_name_from_url, _VersionedKeyStore, parse_region_from_url


def test_base_url():
    expect(bucket_name_from_url('https://s3.amazonaws.com/')).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url('https://wfoobar.localhost:5000/abc')
           ).should.equal("wfoobar")


def test_localhost_without_bucket():
    expect(bucket_name_from_url(
        'https://www.localhost:5000/def')).should.equal(None)

def test_force_ignore_subdomain_for_bucketnames():
    os.environ['S3_IGNORE_SUBDOMAIN_BUCKETNAME'] = '1'
    expect(bucket_name_from_url('https://subdomain.localhost:5000/abc/resource')).should.equal(None)
    del(os.environ['S3_IGNORE_SUBDOMAIN_BUCKETNAME'])
    


def test_versioned_key_store():
    d = _VersionedKeyStore()

    d.should.have.length_of(0)

    d['key'] = [1]

    d.should.have.length_of(1)

    d['key'] = 2
    d.should.have.length_of(1)

    d.should.have.key('key').being.equal(2)

    d.get.when.called_with('key').should.return_value(2)
    d.get.when.called_with('badkey').should.return_value(None)
    d.get.when.called_with('badkey', 'HELLO').should.return_value('HELLO')

    # Tests key[
    d.shouldnt.have.key('badkey')
    d.__getitem__.when.called_with('badkey').should.throw(KeyError)

    d.getlist('key').should.have.length_of(2)
    d.getlist('key').should.be.equal([[1], 2])
    d.getlist('badkey').should.be.none

    d.setlist('key', 1)
    d.getlist('key').should.be.equal([1])

    d.setlist('key', (1, 2))
    d.getlist('key').shouldnt.be.equal((1, 2))
    d.getlist('key').should.be.equal([1, 2])

    d.setlist('key', [[1], [2]])
    d['key'].should.have.length_of(1)
    d.getlist('key').should.be.equal([[1], [2]])


def test_parse_region_from_url():
    expected = 'us-west-2'
    for url in ['http://s3-us-west-2.amazonaws.com/bucket',
                'http://s3.us-west-2.amazonaws.com/bucket',
                'http://bucket.s3-us-west-2.amazonaws.com',
                'https://s3-us-west-2.amazonaws.com/bucket',
                'https://s3.us-west-2.amazonaws.com/bucket',
                'https://bucket.s3-us-west-2.amazonaws.com']:
        parse_region_from_url(url).should.equal(expected)

    expected = 'us-east-1'
    for url in ['http://s3.amazonaws.com/bucket',
                'http://bucket.s3.amazonaws.com',
                'https://s3.amazonaws.com/bucket',
                'https://bucket.s3.amazonaws.com']:
        parse_region_from_url(url).should.equal(expected)
