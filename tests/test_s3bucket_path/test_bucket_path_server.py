from __future__ import unicode_literals
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_s3_server_get():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.get('/')

    res.data.should.contain(b'ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar', server.BASE_URL)
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain(b'<Name>foobar</Name>')

    res = test_client.get('/foobar', server.BASE_URL)
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.put('/foobar2/', server.BASE_URL)
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain(b'<Name>foobar2</Name>')

    res = test_client.get('/foobar2/', server.BASE_URL)
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.get('/missing-bucket', server.BASE_URL)
    res.status_code.should.equal(404)

    res = test_client.put(
        '/foobar/bar', server.BASE_URL, data='test value')
    res.status_code.should.equal(200)

    res = test_client.get('/foobar/bar', server.BASE_URL)
    res.status_code.should.equal(200)
    res.data.should.equal(b"test value")


def test_s3_server_post_to_bucket():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar2', server.BASE_URL)
    res.status_code.should.equal(200)

    test_client.post('/foobar2', server.BASE_URL, data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/foobar2/the-key', server.BASE_URL)
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")


def test_s3_server_put_ipv6():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar2', 'http://[::]:5000/')
    res.status_code.should.equal(200)

    test_client.post('/foobar2', "https://[::]:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/foobar2/the-key', 'http://[::]:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")


def test_s3_server_put_ipv4():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar2', 'http://127.0.0.1:5000/')
    res.status_code.should.equal(200)

    test_client.post('/foobar2', "https://127.0.0.1:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/foobar2/the-key', 'http://127.0.0.1:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")
