import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("dynamodb2")


def test_table_list():
    test_client = server.app.test_client()
    res = test_client.get('/')
    res.status_code.should.equal(404)

    headers = {'X-Amz-Target': 'TestTable.ListTables'}
    res = test_client.get('/', headers=headers)
    res.data.should.contain('TableNames')
