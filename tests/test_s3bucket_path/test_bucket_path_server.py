from __future__ import unicode_literals
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''

HEADERS = {'host': 's3.amazonaws.com'}


def test_s3_server_get():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.get('/', headers=HEADERS)

    res.data.should.contain(b'ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar/', 'http://localhost:5000', headers=HEADERS)
    res.status_code.should.equal(200)

    res = test_client.get('/', headers=HEADERS)
    res.data.should.contain(b'<Name>foobar</Name>')

    res = test_client.get('/foobar/', 'http://localhost:5000', headers=HEADERS)
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.get('/missing-bucket/', 'http://localhost:5000', headers=HEADERS)
    res.status_code.should.equal(404)

    res = test_client.put('/foobar/bar/', 'http://localhost:5000', data='test value', headers=HEADERS)
    res.status_code.should.equal(200)

    res = test_client.get('/foobar/bar/', 'http://localhost:5000', headers=HEADERS)
    res.status_code.should.equal(200)
    res.data.should.equal(b"test value")


def test_s3_server_post_to_bucket():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar2/', 'http://localhost:5000/', headers=HEADERS)
    res.status_code.should.equal(200)

    test_client.post('/foobar2/', "https://localhost:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    }, headers=HEADERS)

    res = test_client.get('/foobar2/the-key/', 'http://localhost:5000/', headers=HEADERS)
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")
