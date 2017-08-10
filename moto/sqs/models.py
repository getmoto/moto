from __future__ import unicode_literals

import base64
import hashlib
import re
import six
import struct
from xml.sax.saxutils import escape

import boto.sqs

from moto.core import BaseBackend, BaseModel
from moto.core.utils import camelcase_to_underscores, get_random_message_id, unix_time, unix_time_millis
from .utils import generate_receipt_handle
from .exceptions import (
    ReceiptHandleIsInvalid,
    MessageNotInflight
)

DEFAULT_ACCOUNT_ID = 123456789012
DEFAULT_SENDER_ID = "AIDAIT2UOQQY3AUEKVGXU"

TRANSPORT_TYPE_ENCODINGS = {'String': b'\x01', 'Binary': b'\x02', 'Number': b'\x01'}


class Message(BaseModel):

    def __init__(self, message_id, body):
        self.id = message_id
        self._body = body
        self.message_attributes = {}
        self.receipt_handle = None
        self.sender_id = DEFAULT_SENDER_ID
        self.sent_timestamp = None
        self.approximate_first_receive_timestamp = None
        self.approximate_receive_count = 0
        self.visible_at = 0
        self.delayed_until = 0

    @property
    def body_md5(self):
        md5 = hashlib.md5()
        md5.update(self._body.encode('utf-8'))
        return md5.hexdigest()

    @property
    def attribute_md5(self):
        """
        The MD5 of all attributes is calculated by first generating a
        utf-8 string from each attribute and MD5-ing the concatenation
        of them all. Each attribute is encoded with some bytes that
        describe the length of each part and the type of attribute.

        Not yet implemented:
            List types (https://github.com/aws/aws-sdk-java/blob/7844c64cf248aed889811bf2e871ad6b276a89ca/aws-java-sdk-sqs/src/main/java/com/amazonaws/services/sqs/MessageMD5ChecksumHandler.java#L58k)
        """
        def utf8(str):
            if isinstance(str, six.string_types):
                return str.encode('utf-8')
            return str
        md5 = hashlib.md5()
        for name in sorted(self.message_attributes.keys()):
            attr = self.message_attributes[name]
            data_type = attr['data_type']

            encoded = utf8('')
            # Each part of each attribute is encoded right after it's
            # own length is packed into a 4-byte integer
            # 'timestamp' -> b'\x00\x00\x00\t'
            encoded += struct.pack("!I", len(utf8(name))) + utf8(name)
            # The datatype is additionally given a final byte
            # representing which type it is
            encoded += struct.pack("!I", len(data_type)) + utf8(data_type)
            encoded += TRANSPORT_TYPE_ENCODINGS[data_type]

            if data_type == 'String' or data_type == 'Number':
                value = attr['string_value']
            elif data_type == 'Binary':
                print(data_type, attr['binary_value'], type(attr['binary_value']))
                value = base64.b64decode(attr['binary_value'])
            else:
                print("Moto hasn't implemented MD5 hashing for {} attributes".format(data_type))
                # The following should be enough of a clue to users that
                # they are not, in fact, looking at a correct MD5 while
                # also following the character and length constraints of
                # MD5 so as not to break client softwre
                return('deadbeefdeadbeefdeadbeefdeadbeef')

            encoded += struct.pack("!I", len(utf8(value))) + utf8(value)

            md5.update(encoded)
        return md5.hexdigest()

    @property
    def body(self):
        return escape(self._body)

    def mark_sent(self, delay_seconds=None):
        self.sent_timestamp = int(unix_time_millis())
        if delay_seconds:
            self.delay(delay_seconds=delay_seconds)

    def mark_received(self, visibility_timeout=None):
        """
        When a message is received we will set the first receive timestamp,
        tap the ``approximate_receive_count`` and the ``visible_at`` time.
        """
        if visibility_timeout:
            visibility_timeout = int(visibility_timeout)
        else:
            visibility_timeout = 0

        if not self.approximate_first_receive_timestamp:
            self.approximate_first_receive_timestamp = int(unix_time_millis())

        self.approximate_receive_count += 1

        # Make message visible again in the future unless its
        # destroyed.
        if visibility_timeout:
            self.change_visibility(visibility_timeout)

        self.receipt_handle = generate_receipt_handle()

    def change_visibility(self, visibility_timeout):
        # We're dealing with milliseconds internally
        visibility_timeout_msec = int(visibility_timeout) * 1000
        self.visible_at = unix_time_millis() + visibility_timeout_msec

    def delay(self, delay_seconds):
        delay_msec = int(delay_seconds) * 1000
        self.delayed_until = unix_time_millis() + delay_msec

    @property
    def visible(self):
        current_time = unix_time_millis()
        if current_time > self.visible_at:
            return True
        return False

    @property
    def delayed(self):
        current_time = unix_time_millis()
        if current_time < self.delayed_until:
            return True
        return False


class Queue(BaseModel):
    camelcase_attributes = ['ApproximateNumberOfMessages',
                            'ApproximateNumberOfMessagesDelayed',
                            'ApproximateNumberOfMessagesNotVisible',
                            'CreatedTimestamp',
                            'DelaySeconds',
                            'LastModifiedTimestamp',
                            'MaximumMessageSize',
                            'MessageRetentionPeriod',
                            'QueueArn',
                            'ReceiveMessageWaitTimeSeconds',
                            'VisibilityTimeout',
                            'WaitTimeSeconds']

    def __init__(self, name, visibility_timeout, wait_time_seconds, region):
        self.name = name
        self.visibility_timeout = visibility_timeout or 30
        self.region = region

        # wait_time_seconds will be set to immediate return messages
        self.wait_time_seconds = int(wait_time_seconds) if wait_time_seconds else 0
        self._messages = []

        now = unix_time()

        self.created_timestamp = now
        self.delay_seconds = 0
        self.last_modified_timestamp = now
        self.maximum_message_size = 64 << 10
        self.message_retention_period = 86400 * 4  # four days
        self.queue_arn = 'arn:aws:sqs:{0}:123456789012:{1}'.format(
            self.region, self.name)
        self.receive_message_wait_time_seconds = 0

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        sqs_backend = sqs_backends[region_name]
        return sqs_backend.create_queue(
            name=properties['QueueName'],
            visibility_timeout=properties.get('VisibilityTimeout'),
            wait_time_seconds=properties.get('WaitTimeSeconds')
        )

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        queue_name = properties['QueueName']

        sqs_backend = sqs_backends[region_name]
        queue = sqs_backend.get_queue(queue_name)
        if 'VisibilityTimeout' in properties:
            queue.visibility_timeout = int(properties['VisibilityTimeout'])

        if 'WaitTimeSeconds' in properties:
            queue.wait_time_seconds = int(properties['WaitTimeSeconds'])
        return queue

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        queue_name = properties['QueueName']
        sqs_backend = sqs_backends[region_name]
        sqs_backend.delete_queue(queue_name)

    @property
    def approximate_number_of_messages_delayed(self):
        return len([m for m in self._messages if m.delayed])

    @property
    def approximate_number_of_messages_not_visible(self):
        return len([m for m in self._messages if not m.visible])

    @property
    def approximate_number_of_messages(self):
        return len(self.messages)

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def attributes(self):
        result = {}
        for attribute in self.camelcase_attributes:
            result[attribute] = getattr(
                self, camelcase_to_underscores(attribute))
        return result

    def url(self, request_url):
        return "{0}://{1}/123456789012/{2}".format(request_url.scheme, request_url.netloc, self.name)

    @property
    def messages(self):
        return [message for message in self._messages if message.visible and not message.delayed]

    def add_message(self, message):
        self._messages.append(message)

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            return self.queue_arn
        elif attribute_name == 'QueueName':
            return self.name
        raise UnformattedGetAttTemplateException()


class SQSBackend(BaseBackend):

    def __init__(self, region_name):
        self.region_name = region_name
        self.queues = {}
        super(SQSBackend, self).__init__()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_queue(self, name, visibility_timeout, wait_time_seconds):
        queue = self.queues.get(name)
        if queue is None:
            queue = Queue(name, visibility_timeout,
                          wait_time_seconds, self.region_name)
            self.queues[name] = queue
        return queue

    def list_queues(self, queue_name_prefix):
        re_str = '.*'
        if queue_name_prefix:
            re_str = '^{0}.*'.format(queue_name_prefix)
        prefix_re = re.compile(re_str)
        qs = []
        for name, q in self.queues.items():
            if prefix_re.search(name):
                qs.append(q)
        return qs

    def get_queue(self, queue_name):
        return self.queues.get(queue_name, None)

    def delete_queue(self, queue_name):
        if queue_name in self.queues:
            return self.queues.pop(queue_name)
        return False

    def set_queue_attribute(self, queue_name, key, value):
        queue = self.get_queue(queue_name)
        setattr(queue, key, value)
        return queue

    def send_message(self, queue_name, message_body, message_attributes=None, delay_seconds=None):

        queue = self.get_queue(queue_name)

        if delay_seconds:
            delay_seconds = int(delay_seconds)
        else:
            delay_seconds = queue.delay_seconds

        message_id = get_random_message_id()
        message = Message(message_id, message_body)

        if message_attributes:
            message.message_attributes = message_attributes

        message.mark_sent(
            delay_seconds=delay_seconds
        )

        queue.add_message(message)

        return message

    def receive_messages(self, queue_name, count, wait_seconds_timeout, visibility_timeout):
        """
        Attempt to retrieve visible messages from a queue.

        If a message was read by client and not deleted it is considered to be
        "inflight" and cannot be read. We make attempts to obtain ``count``
        messages but we may return less if messages are in-flight or there
        are simple not enough messages in the queue.

        :param string queue_name: The name of the queue to read from.
        :param int count: The maximum amount of messages to retrieve.
        :param int visibility_timeout: The number of seconds the message should remain invisible to other queue readers.
        :param int wait_seconds_timeout:  The duration (in seconds) for which the call waits for a message to arrive in
         the queue before returning. If a message is available, the call returns sooner than WaitTimeSeconds
        """
        queue = self.get_queue(queue_name)
        result = []

        polling_end = unix_time() + wait_seconds_timeout

        # queue.messages only contains visible messages
        while True:

            if result or (wait_seconds_timeout and unix_time() > polling_end):
                break

            if len(queue.messages) == 0:
                # we want to break here, otherwise it will be an infinite loop
                if wait_seconds_timeout == 0:
                    break

                import time
                time.sleep(0.001)
                continue

            for message in queue.messages:
                if not message.visible:
                    continue
                message.mark_received(
                    visibility_timeout=visibility_timeout
                )
                result.append(message)
                if len(result) >= count:
                    break

        return result

    def delete_message(self, queue_name, receipt_handle):
        queue = self.get_queue(queue_name)
        new_messages = []
        for message in queue._messages:
            # Only delete message if it is not visible and the reciept_handle
            # matches.
            if message.receipt_handle == receipt_handle:
                continue
            new_messages.append(message)
        queue._messages = new_messages

    def change_message_visibility(self, queue_name, receipt_handle, visibility_timeout):
        queue = self.get_queue(queue_name)
        for message in queue._messages:
            if message.receipt_handle == receipt_handle:
                if message.visible:
                    raise MessageNotInflight
                message.change_visibility(visibility_timeout)
                return
        raise ReceiptHandleIsInvalid

    def purge_queue(self, queue_name):
        queue = self.get_queue(queue_name)
        queue._messages = []


sqs_backends = {}
for region in boto.sqs.regions():
    sqs_backends[region.name] = SQSBackend(region.name)
