import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("s3bucket_path")


def test_s3_server_get():
    test_client = server.app.test_client()
    res = test_client.get('/')

    res.data.should.contain('ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    test_client = server.app.test_client()
    res = test_client.put('/foobar', 'http://localhost:5000')
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain('<Name>foobar</Name>')

    res = test_client.get('/foobar', 'http://localhost:5000')
    res.status_code.should.equal(200)
    res.data.should.contain("ListBucketResult")

    res = test_client.put('/foobar/bar', 'http://localhost:5000', data='test value')
    res.status_code.should.equal(200)

    res = test_client.get('/foobar/bar', 'http://localhost:5000')
    res.status_code.should.equal(200)
    res.data.should.equal("test value")


def test_s3_server_post_to_bucket():
    test_client = server.app.test_client()
    res = test_client.put('/foobar', 'http://localhost:5000/')
    res.status_code.should.equal(200)

    test_client.post('/foobar', "https://localhost:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/foobar/the-key', 'http://localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal("nothing")
