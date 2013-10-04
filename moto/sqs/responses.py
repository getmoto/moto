from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import sqs_backend


class QueuesResponse(BaseResponse):

    def create_queue(self):
        visibility_timeout = None
        if 'Attribute.1.Name' in self.querystring and self.querystring.get('Attribute.1.Name')[0] == 'VisibilityTimeout':
            visibility_timeout = self.querystring.get("Attribute.1.Value")[0]

        queue_name = self.querystring.get("QueueName")[0]
        queue = sqs_backend.create_queue(queue_name, visibility_timeout=visibility_timeout)
        template = Template(CREATE_QUEUE_RESPONSE)
        return template.render(queue=queue)

    def get_queue_url(self):
        queue_name = self.querystring.get("QueueName")[0]
        queue = sqs_backend.get_queue(queue_name)
        if queue:
            template = Template(GET_QUEUE_URL_RESPONSE)
            return template.render(queue=queue)
        else:
            return "", dict(status=404)

    def list_queues(self):
        queues = sqs_backend.list_queues()
        template = Template(LIST_QUEUES_RESPONSE)
        return template.render(queues=queues)


class QueueResponse(BaseResponse):
    def get_queue_attributes(self):
        queue_name = self.path.split("/")[-1]
        queue = sqs_backend.get_queue(queue_name)
        template = Template(GET_QUEUE_ATTRIBUTES_RESPONSE)
        return template.render(queue=queue)

    def set_queue_attributes(self):
        queue_name = self.path.split("/")[-1]
        key = camelcase_to_underscores(self.querystring.get('Attribute.Name')[0])
        value = self.querystring.get('Attribute.Value')[0]
        sqs_backend.set_queue_attribute(queue_name, key, value)
        return SET_QUEUE_ATTRIBUTE_RESPONSE

    def delete_queue(self):
        queue_name = self.path.split("/")[-1]
        queue = sqs_backend.delete_queue(queue_name)
        if not queue:
            return "A queue with name {0} does not exist".format(queue_name), dict(status=404)
        template = Template(DELETE_QUEUE_RESPONSE)
        return template.render(queue=queue)

    def send_message(self):
        message = self.querystring.get("MessageBody")[0]
        queue_name = self.path.split("/")[-1]
        message = sqs_backend.send_message(queue_name, message)
        template = Template(SEND_MESSAGE_RESPONSE)
        return template.render(message=message)

    def send_message_batch(self):
        """
        The querystring comes like this

        'SendMessageBatchRequestEntry.1.DelaySeconds': ['0'],
        'SendMessageBatchRequestEntry.1.MessageBody': ['test message 1'],
        'SendMessageBatchRequestEntry.1.Id': ['6d0f122d-4b13-da2c-378f-e74244d8ad11']
        'SendMessageBatchRequestEntry.2.Id': ['ff8cbf59-70a2-c1cb-44c7-b7469f1ba390'],
        'SendMessageBatchRequestEntry.2.MessageBody': ['test message 2'],
        'SendMessageBatchRequestEntry.2.DelaySeconds': ['0'],
        """

        queue_name = self.path.split("/")[-1]

        messages = []
        for index in range(1, 11):
            # Loop through looking for messages
            message_key = 'SendMessageBatchRequestEntry.{0}.MessageBody'.format(index)
            message_body = self.querystring.get(message_key)
            if not message_body:
                # Found all messages
                break

            message_user_id_key = 'SendMessageBatchRequestEntry.{0}.Id'.format(index)
            message_user_id = self.querystring.get(message_user_id_key)[0]
            delay_key = 'SendMessageBatchRequestEntry.{0}.DelaySeconds'.format(index)
            delay_seconds = self.querystring.get(delay_key, [None])[0]
            message = sqs_backend.send_message(queue_name, message_body[0], delay_seconds=delay_seconds)
            message.user_id = message_user_id
            messages.append(message)

        template = Template(SEND_MESSAGE_BATCH_RESPONSE)
        return template.render(messages=messages)

    def delete_message(self):
        queue_name = self.path.split("/")[-1]
        receipt_handle = self.querystring.get("ReceiptHandle")[0]
        sqs_backend.delete_message(queue_name, receipt_handle)
        template = Template(DELETE_MESSAGE_RESPONSE)
        return template.render()

    def delete_message_batch(self):
        """
        The querystring comes like this

        'DeleteMessageBatchRequestEntry.1.Id': ['message_1'],
        'DeleteMessageBatchRequestEntry.1.ReceiptHandle': ['asdfsfs...'],
        'DeleteMessageBatchRequestEntry.2.Id': ['message_2'],
        'DeleteMessageBatchRequestEntry.2.ReceiptHandle': ['zxcvfda...'],
        ...
        """
        queue_name = self.path.split("/")[-1]

        message_ids = []
        for index in range(1, 11):
            # Loop through looking for messages
            receipt_key = 'DeleteMessageBatchRequestEntry.{0}.ReceiptHandle'.format(index)
            receipt_handle = self.querystring.get(receipt_key)
            if not receipt_handle:
                # Found all messages
                break

            sqs_backend.delete_message(queue_name, receipt_handle[0])

            message_user_id_key = 'DeleteMessageBatchRequestEntry.{0}.Id'.format(index)
            message_user_id = self.querystring.get(message_user_id_key)[0]
            message_ids.append(message_user_id)

        template = Template(DELETE_MESSAGE_BATCH_RESPONSE)
        return template.render(message_ids=message_ids)

    def receive_message(self):
        queue_name = self.path.split("/")[-1]
        message_count = int(self.querystring.get("MaxNumberOfMessages")[0])
        messages = sqs_backend.receive_messages(queue_name, message_count)
        template = Template(RECEIVE_MESSAGE_RESPONSE)
        return template.render(messages=messages)


CREATE_QUEUE_RESPONSE = """<CreateQueueResponse>
    <CreateQueueResult>
        <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
        <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
    </CreateQueueResult>
    <ResponseMetadata>
        <RequestId>
            7a62c49f-347e-4fc4-9331-6e8e7a96aa73
        </RequestId>
    </ResponseMetadata>
</CreateQueueResponse>"""

GET_QUEUE_URL_RESPONSE = """<GetQueueUrlResponse>
    <GetQueueUrlResult>
        <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
    </GetQueueUrlResult>
    <ResponseMetadata>
        <RequestId>470a6f13-2ed9-4181-ad8a-2fdea142988e</RequestId>
    </ResponseMetadata>
</GetQueueUrlResponse>"""

LIST_QUEUES_RESPONSE = """<ListQueuesResponse>
    <ListQueuesResult>
        {% for queue in queues %}
            <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
            <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
        {% endfor %}
    </ListQueuesResult>
    <ResponseMetadata>
        <RequestId>
            725275ae-0b9b-4762-b238-436d7c65a1ac
        </RequestId>
    </ResponseMetadata>
</ListQueuesResponse>"""

DELETE_QUEUE_RESPONSE = """<DeleteQueueResponse>
    <ResponseMetadata>
        <RequestId>
            6fde8d1e-52cd-4581-8cd9-c512f4c64223
        </RequestId>
    </ResponseMetadata>
</DeleteQueueResponse>"""

GET_QUEUE_ATTRIBUTES_RESPONSE = """<GetQueueAttributesResponse>
  <GetQueueAttributesResult>
    {% for key, value in queue.attributes.items() %}
        <Attribute>
          <Name>{{ key }}</Name>
          <Value>{{ value }}</Value>
        </Attribute>
    {% endfor %}
  </GetQueueAttributesResult>
  <ResponseMetadata>
    <RequestId>1ea71be5-b5a2-4f9d-b85a-945d8d08cd0b</RequestId>
  </ResponseMetadata>
</GetQueueAttributesResponse>"""

SET_QUEUE_ATTRIBUTE_RESPONSE = """<SetQueueAttributesResponse>
    <ResponseMetadata>
        <RequestId>
            e5cca473-4fc0-4198-a451-8abb94d02c75
        </RequestId>
    </ResponseMetadata>
</SetQueueAttributesResponse>"""

SEND_MESSAGE_RESPONSE = """<SendMessageResponse>
    <SendMessageResult>
        <MD5OfMessageBody>
            {{ message.md5 }}
        </MD5OfMessageBody>
        <MessageId>
            {{ message.id }}
        </MessageId>
    </SendMessageResult>
    <ResponseMetadata>
        <RequestId>
            27daac76-34dd-47df-bd01-1f6e873584a0
        </RequestId>
    </ResponseMetadata>
</SendMessageResponse>"""

RECEIVE_MESSAGE_RESPONSE = """<ReceiveMessageResponse>
  <ReceiveMessageResult>
    {% for message in messages %}
        <Message>
          <MessageId>
            {{ message.id }}
          </MessageId>
          <ReceiptHandle>
            MbZj6wDWli+JvwwJaBV+3dcjk2YW2vA3+STFFljTM8tJJg6HRG6PYSasuWXPJB+Cw
            Lj1FjgXUv1uSj1gUPAWV66FU/WeR4mq2OKpEGYWbnLmpRCJVAyeMjeU5ZBdtcQ+QE
            auMZc8ZRv37sIW2iJKq3M9MFx1YvV11A2x/KSbkJ0=
          </ReceiptHandle>
          <MD5OfBody>
            {{ message.md5 }}
          </MD5OfBody>
          <Body>{{ message.body }}</Body>
        </Message>
    {% endfor %}
  </ReceiveMessageResult>
  <ResponseMetadata>
    <RequestId>
      b6633655-283d-45b4-aee4-4e84e0ae6afa
    </RequestId>
  </ResponseMetadata>
</ReceiveMessageResponse>"""

SEND_MESSAGE_BATCH_RESPONSE = """<SendMessageBatchResponse>
<SendMessageBatchResult>
    {% for message in messages %}
        <SendMessageBatchResultEntry>
            <Id>{{ message.user_id }}</Id>
            <MessageId>{{ message.id }}</MessageId>
            <MD5OfMessageBody>{{ message.md5 }}</MD5OfMessageBody>
        </SendMessageBatchResultEntry>
    {% endfor %}
</SendMessageBatchResult>
<ResponseMetadata>
    <RequestId>ca1ad5d0-8271-408b-8d0f-1351bf547e74</RequestId>
</ResponseMetadata>
</SendMessageBatchResponse>"""

DELETE_MESSAGE_RESPONSE = """<DeleteMessageResponse>
    <ResponseMetadata>
        <RequestId>
            b5293cb5-d306-4a17-9048-b263635abe42
        </RequestId>
    </ResponseMetadata>
</DeleteMessageResponse>"""

DELETE_MESSAGE_BATCH_RESPONSE = """<DeleteMessageBatchResponse>
    <DeleteMessageBatchResult>
        {% for message_id in message_ids %}
            <DeleteMessageBatchResultEntry>
                <Id>{{ message_id }}</Id>
            </DeleteMessageBatchResultEntry>
        {% endfor %}
    </DeleteMessageBatchResult>
    <ResponseMetadata>
        <RequestId>d6f86b7a-74d1-4439-b43f-196a1e29cd85</RequestId>
    </ResponseMetadata>
</DeleteMessageBatchResponse>"""
