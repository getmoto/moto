from __future__ import unicode_literals

import moto.settings
from sure import expect
from moto.s3bucket_path.utils import bucket_name_from_url


def test_base_url():
    expect(bucket_name_from_url('https://s3.amazonaws.com/')).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url('{}/wfoobar/abc'.format(
        moto.settings.SERVER_BASE_URL))
           ).should.equal("wfoobar")


def test_localhost_without_bucket():
    expect(bucket_name_from_url('https://www.localhost:5000')).should.equal(None)
