from __future__ import unicode_literals
from sure import expect
from moto.s3.utils import bucket_name_from_url, _VersionedKeyStore


def test_base_url():
    expect(bucket_name_from_url('https://s3.amazonaws.com/')).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url('https://wfoobar.localhost:5000/abc')
           ).should.equal("wfoobar")


def test_localhost_without_bucket():
    expect(bucket_name_from_url(
        'https://www.localhost:5000/def')).should.equal(None)


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
