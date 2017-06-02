from __future__ import unicode_literals

import re
import sure  # noqa
import threading
import time

import moto.server as server

'''
Test the different server responses
'''


def test_sqs_list_identities():
    backend = server.create_backend_app("sqs")
    test_client = backend.test_client()

    res = test_client.get('/?Action=ListQueues')
    res.data.should.contain(b"ListQueuesResponse")

    res = test_client.put('/?Action=CreateQueue&QueueName=testqueue')
    res = test_client.put('/?Action=CreateQueue&QueueName=otherqueue')

    res = test_client.get('/?Action=ListQueues&QueueNamePrefix=other')
    res.data.should_not.contain(b'testqueue')

    res = test_client.put(
        '/123/testqueue?MessageBody=test-message&Action=SendMessage')

    res = test_client.get(
        '/123/testqueue?Action=ReceiveMessage&MaxNumberOfMessages=1')

    message = re.search("<Body>(.*?)</Body>",
                        res.data.decode('utf-8')).groups()[0]
    message.should.equal('test-message')


def test_messages_polling():
    backend = server.create_backend_app("sqs")
    test_client = backend.test_client()
    messages = []

    test_client.put('/?Action=CreateQueue&QueueName=testqueue')

    def insert_messages():
        messages_count = 5
        while messages_count > 0:
            test_client.put(
                '/123/testqueue?MessageBody=test-message&Action=SendMessage'
                '&Attribute.1.Name=WaitTimeSeconds&Attribute.1.Value=10'
            )
            messages_count -= 1
            time.sleep(.5)

    def get_messages():
        count = 0
        while count < 5:
            msg_res = test_client.get(
                '/123/testqueue?Action=ReceiveMessage&MaxNumberOfMessages=1&WaitTimeSeconds=5'
            )
            new_msgs = re.findall("<Body>(.*?)</Body>",
                                  msg_res.data.decode('utf-8'))
            count += len(new_msgs)
            messages.append(new_msgs)

    get_messages_thread = threading.Thread(target=get_messages)
    insert_messages_thread = threading.Thread(target=insert_messages)

    get_messages_thread.start()
    insert_messages_thread.start()

    get_messages_thread.join()
    insert_messages_thread.join()

    # got each message in a separate call to ReceiveMessage, despite the long
    # WaitTimeSeconds
    assert len(messages) == 5
