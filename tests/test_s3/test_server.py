import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("s3")


def test_s3_server_get():
    test_client = server.app.test_client()
    res = test_client.get('/')

    res.data.should.contain('ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    test_client = server.app.test_client()
    res = test_client.put('/', 'http://foobar.localhost:5000/')
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain('<Name>foobar</Name>')

    res = test_client.get('/', 'http://foobar.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.contain("ListBucketResult")

    res = test_client.put('/bar', 'http://foobar.localhost:5000/', data='test value')
    res.status_code.should.equal(200)

    res = test_client.get('/bar', 'http://foobar.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal("test value")
