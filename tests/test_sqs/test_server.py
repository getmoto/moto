import re
import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("sqs")


def test_sqs_list_identities():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=ListQueues')
    res.data.should.contain("ListQueuesResponse")

    res = test_client.put('/?Action=CreateQueue&QueueName=testqueue')

    res = test_client.put(
        '/123/testqueue?MessageBody=test-message&Action=SendMessage')

    res = test_client.get(
        '/123/testqueue?Action=ReceiveMessage&MaxNumberOfMessages=1')
    message = re.search("<Body>(.*?)</Body>", res.data).groups()[0]
    message.should.equal('test-message')
