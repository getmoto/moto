from __future__ import unicode_literals
from six.moves.urllib.parse import urlparse

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .utils import parse_message_attributes
from .models import sqs_backends
from .exceptions import (
    MessageAttributesInvalid,
    MessageNotInflight,
    ReceiptHandleIsInvalid
)

MAXIMUM_VISIBILTY_TIMEOUT = 43200
MAXIMUM_MESSAGE_LENGTH = 262144  # 256 KiB
DEFAULT_RECEIVED_MESSAGES = 1
SQS_REGION_REGEX = r'://(.+?)\.queue\.amazonaws\.com'


class SQSResponse(BaseResponse):

    region_regex = SQS_REGION_REGEX

    @property
    def sqs_backend(self):
        return sqs_backends[self.region]

    @property
    def attribute(self):
        if not hasattr(self, '_attribute'):
            self._attribute = dict([(a['name'], a['value'])
                                    for a in self._get_list_prefix('Attribute')])
        return self._attribute

    def _get_queue_name(self):
        try:
            queue_name = self.querystring.get('QueueUrl')[0].split("/")[-1]
        except TypeError:
            # Fallback to reading from the URL
            queue_name = self.path.split("/")[-1]
        return queue_name

    def _get_validated_visibility_timeout(self):
        """
        :raises ValueError: If specified visibility timeout exceeds MAXIMUM_VISIBILTY_TIMEOUT
        :raises TypeError: If visibility timeout was not specified
        """
        visibility_timeout = int(self.querystring.get("VisibilityTimeout")[0])

        if visibility_timeout > MAXIMUM_VISIBILTY_TIMEOUT:
            raise ValueError

        return visibility_timeout

    def call_action(self):
        status_code, headers, body = super(SQSResponse, self).call_action()
        if status_code == 404:
            return 404, headers, ERROR_INEXISTENT_QUEUE
        return status_code, headers, body

    def create_queue(self):
        request_url = urlparse(self.uri)
        queue_name = self.querystring.get("QueueName")[0]
        queue = self.sqs_backend.create_queue(queue_name, visibility_timeout=self.attribute.get('VisibilityTimeout'),
                                              wait_time_seconds=self.attribute.get('WaitTimeSeconds'))
        template = self.response_template(CREATE_QUEUE_RESPONSE)
        return template.render(queue=queue, request_url=request_url)

    def get_queue_url(self):
        request_url = urlparse(self.uri)
        queue_name = self.querystring.get("QueueName")[0]
        queue = self.sqs_backend.get_queue(queue_name)
        if queue:
            template = self.response_template(GET_QUEUE_URL_RESPONSE)
            return template.render(queue=queue, request_url=request_url)
        else:
            return "", dict(status=404)

    def list_queues(self):
        request_url = urlparse(self.uri)
        queue_name_prefix = self.querystring.get("QueueNamePrefix", [None])[0]
        queues = self.sqs_backend.list_queues(queue_name_prefix)
        template = self.response_template(LIST_QUEUES_RESPONSE)
        return template.render(queues=queues, request_url=request_url)

    def change_message_visibility(self):
        queue_name = self._get_queue_name()
        receipt_handle = self.querystring.get("ReceiptHandle")[0]

        try:
            visibility_timeout = self._get_validated_visibility_timeout()
        except ValueError:
            return ERROR_MAX_VISIBILITY_TIMEOUT_RESPONSE, dict(status=400)

        try:
            self.sqs_backend.change_message_visibility(
                queue_name=queue_name,
                receipt_handle=receipt_handle,
                visibility_timeout=visibility_timeout
            )
        except (ReceiptHandleIsInvalid, MessageNotInflight) as e:
            return "Invalid request: {0}".format(e.description), dict(status=e.status_code)

        template = self.response_template(CHANGE_MESSAGE_VISIBILITY_RESPONSE)
        return template.render()

    def get_queue_attributes(self):
        queue_name = self._get_queue_name()
        queue = self.sqs_backend.get_queue(queue_name)
        template = self.response_template(GET_QUEUE_ATTRIBUTES_RESPONSE)
        return template.render(queue=queue)

    def set_queue_attributes(self):
        queue_name = self._get_queue_name()
        if "Attribute.Name" in self.querystring:
            key = camelcase_to_underscores(
                self.querystring.get("Attribute.Name")[0])
            value = self.querystring.get("Attribute.Value")[0]
            self.sqs_backend.set_queue_attribute(queue_name, key, value)
        for a in self._get_list_prefix("Attribute"):
            key = camelcase_to_underscores(a["name"])
            value = a["value"]
            self.sqs_backend.set_queue_attribute(queue_name, key, value)
        return SET_QUEUE_ATTRIBUTE_RESPONSE

    def delete_queue(self):
        queue_name = self._get_queue_name()
        queue = self.sqs_backend.delete_queue(queue_name)
        if not queue:
            return "A queue with name {0} does not exist".format(queue_name), dict(status=404)

        template = self.response_template(DELETE_QUEUE_RESPONSE)
        return template.render(queue=queue)

    def send_message(self):
        message = self.querystring.get("MessageBody")[0]
        delay_seconds = self.querystring.get('DelaySeconds')

        if len(message) > MAXIMUM_MESSAGE_LENGTH:
            return ERROR_TOO_LONG_RESPONSE, dict(status=400)

        if delay_seconds:
            delay_seconds = int(delay_seconds[0])
        else:
            delay_seconds = 0

        try:
            message_attributes = parse_message_attributes(self.querystring)
        except MessageAttributesInvalid as e:
            return e.description, dict(status=e.status_code)

        queue_name = self._get_queue_name()

        message = self.sqs_backend.send_message(
            queue_name,
            message,
            message_attributes=message_attributes,
            delay_seconds=delay_seconds
        )
        template = self.response_template(SEND_MESSAGE_RESPONSE)
        return template.render(message=message, message_attributes=message_attributes)

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

        queue_name = self._get_queue_name()

        messages = []
        for index in range(1, 11):
            # Loop through looking for messages
            message_key = 'SendMessageBatchRequestEntry.{0}.MessageBody'.format(
                index)
            message_body = self.querystring.get(message_key)
            if not message_body:
                # Found all messages
                break

            message_user_id_key = 'SendMessageBatchRequestEntry.{0}.Id'.format(
                index)
            message_user_id = self.querystring.get(message_user_id_key)[0]
            delay_key = 'SendMessageBatchRequestEntry.{0}.DelaySeconds'.format(
                index)
            delay_seconds = self.querystring.get(delay_key, [None])[0]
            message = self.sqs_backend.send_message(
                queue_name, message_body[0], delay_seconds=delay_seconds)
            message.user_id = message_user_id

            message_attributes = parse_message_attributes(
                self.querystring, base='SendMessageBatchRequestEntry.{0}.'.format(index))
            if type(message_attributes) == tuple:
                return message_attributes[0], message_attributes[1]
            message.message_attributes = message_attributes

            messages.append(message)

        template = self.response_template(SEND_MESSAGE_BATCH_RESPONSE)
        return template.render(messages=messages)

    def delete_message(self):
        queue_name = self._get_queue_name()
        receipt_handle = self.querystring.get("ReceiptHandle")[0]
        self.sqs_backend.delete_message(queue_name, receipt_handle)
        template = self.response_template(DELETE_MESSAGE_RESPONSE)
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
        queue_name = self._get_queue_name()

        message_ids = []
        for index in range(1, 11):
            # Loop through looking for messages
            receipt_key = 'DeleteMessageBatchRequestEntry.{0}.ReceiptHandle'.format(
                index)
            receipt_handle = self.querystring.get(receipt_key)
            if not receipt_handle:
                # Found all messages
                break

            self.sqs_backend.delete_message(queue_name, receipt_handle[0])

            message_user_id_key = 'DeleteMessageBatchRequestEntry.{0}.Id'.format(
                index)
            message_user_id = self.querystring.get(message_user_id_key)[0]
            message_ids.append(message_user_id)

        template = self.response_template(DELETE_MESSAGE_BATCH_RESPONSE)
        return template.render(message_ids=message_ids)

    def purge_queue(self):
        queue_name = self._get_queue_name()
        self.sqs_backend.purge_queue(queue_name)
        template = self.response_template(PURGE_QUEUE_RESPONSE)
        return template.render()

    def receive_message(self):
        queue_name = self._get_queue_name()
        queue = self.sqs_backend.get_queue(queue_name)

        try:
            message_count = int(self.querystring.get("MaxNumberOfMessages")[0])
        except TypeError:
            message_count = DEFAULT_RECEIVED_MESSAGES

        try:
            wait_time = int(self.querystring.get("WaitTimeSeconds")[0])
        except TypeError:
            wait_time = queue.wait_time_seconds

        try:
            visibility_timeout = self._get_validated_visibility_timeout()
        except TypeError:
            visibility_timeout = queue.visibility_timeout
        except ValueError:
            return ERROR_MAX_VISIBILITY_TIMEOUT_RESPONSE, dict(status=400)

        messages = self.sqs_backend.receive_messages(
            queue_name, message_count, wait_time, visibility_timeout)
        template = self.response_template(RECEIVE_MESSAGE_RESPONSE)
        output = template.render(messages=messages)
        return output


CREATE_QUEUE_RESPONSE = """<CreateQueueResponse>
    <CreateQueueResult>
        <QueueUrl>{{ queue.url(request_url) }}</QueueUrl>
        <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
    </CreateQueueResult>
    <ResponseMetadata>
        <RequestId>7a62c49f-347e-4fc4-9331-6e8e7a96aa73</RequestId>
    </ResponseMetadata>
</CreateQueueResponse>"""

GET_QUEUE_URL_RESPONSE = """<GetQueueUrlResponse>
    <GetQueueUrlResult>
        <QueueUrl>{{ queue.url(request_url) }}</QueueUrl>
    </GetQueueUrlResult>
    <ResponseMetadata>
        <RequestId>470a6f13-2ed9-4181-ad8a-2fdea142988e</RequestId>
    </ResponseMetadata>
</GetQueueUrlResponse>"""

LIST_QUEUES_RESPONSE = """<ListQueuesResponse>
    <ListQueuesResult>
        {% for queue in queues %}
            <QueueUrl>{{ queue.url(request_url) }}</QueueUrl>
        {% endfor %}
    </ListQueuesResult>
    <ResponseMetadata>
        <RequestId>725275ae-0b9b-4762-b238-436d7c65a1ac</RequestId>
    </ResponseMetadata>
</ListQueuesResponse>"""

DELETE_QUEUE_RESPONSE = """<DeleteQueueResponse>
    <ResponseMetadata>
        <RequestId>6fde8d1e-52cd-4581-8cd9-c512f4c64223</RequestId>
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
        <RequestId>e5cca473-4fc0-4198-a451-8abb94d02c75</RequestId>
    </ResponseMetadata>
</SetQueueAttributesResponse>"""

SEND_MESSAGE_RESPONSE = """<SendMessageResponse>
    <SendMessageResult>
        <MD5OfMessageBody>
            {{- message.body_md5 -}}
        </MD5OfMessageBody>
        {% if message.message_attributes.items()|count > 0 %}
        <MD5OfMessageAttributes>{{- message.attribute_md5 -}}</MD5OfMessageAttributes>
        {% endif %}
        <MessageId>
            {{- message.id -}}
        </MessageId>
    </SendMessageResult>
    <ResponseMetadata>
        <RequestId>27daac76-34dd-47df-bd01-1f6e873584a0</RequestId>
    </ResponseMetadata>
</SendMessageResponse>"""

RECEIVE_MESSAGE_RESPONSE = """<ReceiveMessageResponse>
  <ReceiveMessageResult>
    {% for message in messages %}
        <Message>
          <MessageId>{{ message.id }}</MessageId>
          <ReceiptHandle>{{ message.receipt_handle }}</ReceiptHandle>
          <MD5OfBody>{{ message.body_md5 }}</MD5OfBody>
          <Body>{{ message.body }}</Body>
          <Attribute>
            <Name>SenderId</Name>
            <Value>{{ message.sender_id }}</Value>
          </Attribute>
          <Attribute>
            <Name>SentTimestamp</Name>
            <Value>{{ message.sent_timestamp }}</Value>
          </Attribute>
          <Attribute>
            <Name>ApproximateReceiveCount</Name>
            <Value>{{ message.approximate_receive_count }}</Value>
          </Attribute>
          <Attribute>
            <Name>ApproximateFirstReceiveTimestamp</Name>
            <Value>{{ message.approximate_first_receive_timestamp }}</Value>
          </Attribute>
          {% if message.message_attributes.items()|count > 0 %}
          <MD5OfMessageAttributes>{{- message.attribute_md5 -}}</MD5OfMessageAttributes>
          {% endif %}
          {% for name, value in message.message_attributes.items() %}
            <MessageAttribute>
              <Name>{{ name }}</Name>
              <Value>
                <DataType>{{ value.data_type }}</DataType>
                {% if 'Binary' in value.data_type %}
                <BinaryValue>{{ value.binary_value }}</BinaryValue>
                {% else %}
                <StringValue>{{ value.string_value }}</StringValue>
                {% endif %}
              </Value>
            </MessageAttribute>
          {% endfor %}
        </Message>
    {% endfor %}
  </ReceiveMessageResult>
  <ResponseMetadata>
    <RequestId>b6633655-283d-45b4-aee4-4e84e0ae6afa</RequestId>
  </ResponseMetadata>
</ReceiveMessageResponse>"""

SEND_MESSAGE_BATCH_RESPONSE = """<SendMessageBatchResponse>
<SendMessageBatchResult>
    {% for message in messages %}
        <SendMessageBatchResultEntry>
            <Id>{{ message.user_id }}</Id>
            <MessageId>{{ message.id }}</MessageId>
            <MD5OfMessageBody>{{ message.body_md5 }}</MD5OfMessageBody>
            {% if message.message_attributes.items()|count > 0 %}
            <MD5OfMessageAttributes>{{- message.attribute_md5 -}}</MD5OfMessageAttributes>
            {% endif %}
        </SendMessageBatchResultEntry>
    {% endfor %}
</SendMessageBatchResult>
<ResponseMetadata>
    <RequestId>ca1ad5d0-8271-408b-8d0f-1351bf547e74</RequestId>
</ResponseMetadata>
</SendMessageBatchResponse>"""

DELETE_MESSAGE_RESPONSE = """<DeleteMessageResponse>
    <ResponseMetadata>
        <RequestId>b5293cb5-d306-4a17-9048-b263635abe42</RequestId>
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

CHANGE_MESSAGE_VISIBILITY_RESPONSE = """<ChangeMessageVisibilityResponse>
    <ResponseMetadata>
        <RequestId>6a7a282a-d013-4a59-aba9-335b0fa48bed</RequestId>
    </ResponseMetadata>
</ChangeMessageVisibilityResponse>"""

PURGE_QUEUE_RESPONSE = """<PurgeQueueResponse>
    <ResponseMetadata>
        <RequestId>6fde8d1e-52cd-4581-8cd9-c512f4c64223</RequestId>
    </ResponseMetadata>
</PurgeQueueResponse>"""

ERROR_TOO_LONG_RESPONSE = """<ErrorResponse xmlns="http://queue.amazonaws.com/doc/2012-11-05/">
    <Error>
        <Type>Sender</Type>
        <Code>InvalidParameterValue</Code>
        <Message>One or more parameters are invalid. Reason: Message must be shorter than 262144 bytes.</Message>
        <Detail/>
    </Error>
    <RequestId>6fde8d1e-52cd-4581-8cd9-c512f4c64223</RequestId>
</ErrorResponse>"""

ERROR_MAX_VISIBILITY_TIMEOUT_RESPONSE = "Invalid request, maximum visibility timeout is {0}".format(
    MAXIMUM_VISIBILTY_TIMEOUT)

ERROR_INEXISTENT_QUEUE = """<ErrorResponse xmlns="http://queue.amazonaws.com/doc/2012-11-05/">
    <Error>
        <Type>Sender</Type>
        <Code>AWS.SimpleQueueService.NonExistentQueue</Code>
        <Message>The specified queue does not exist for this wsdl version.</Message>
        <Detail/>
    </Error>
    <RequestId>b8bc806b-fa6b-53b5-8be8-cfa2f9836bc3</RequestId>
</ErrorResponse>"""
