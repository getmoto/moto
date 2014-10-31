from __future__ import unicode_literals
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_s3_server_get():
    backend = server.create_backend_app("s3")
    test_client = backend.test_client()

    res = test_client.get('/')

    res.data.should.contain(b'ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    backend = server.create_backend_app("s3")
    test_client = backend.test_client()

    res = test_client.put('/', 'http://foobaz.localhost:5000/')
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain(b'<Name>foobaz</Name>')

    res = test_client.get('/', 'http://foobaz.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.put('/bar', 'http://foobaz.localhost:5000/', data='test value')
    res.status_code.should.equal(200)

    res = test_client.get('/bar', 'http://foobaz.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal(b"test value")


def test_s3_server_post_to_bucket():
    backend = server.create_backend_app("s3")
    test_client = backend.test_client()

    res = test_client.put('/', 'http://tester.localhost:5000/')
    res.status_code.should.equal(200)

    test_client.post('/', "https://tester.localhost:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/the-key', 'http://tester.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")
