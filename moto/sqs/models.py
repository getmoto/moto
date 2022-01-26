import base64
import hashlib
import json
import random
import re
import string

import struct
from copy import deepcopy
from typing import Dict
from xml.sax.saxutils import escape

from moto.core.exceptions import RESTError
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import (
    camelcase_to_underscores,
    get_random_message_id,
    unix_time,
    unix_time_millis,
    tags_from_cloudformation_tags_list,
    BackendDict,
)
from .utils import generate_receipt_handle
from .exceptions import (
    MessageAttributesInvalid,
    QueueDoesNotExist,
    QueueAlreadyExists,
    ReceiptHandleIsInvalid,
    InvalidBatchEntryId,
    BatchRequestTooLong,
    BatchEntryIdsNotDistinct,
    TooManyEntriesInBatchRequest,
    InvalidAttributeName,
    InvalidParameterValue,
    MissingParameter,
    OverLimit,
    InvalidAttributeValue,
)

from moto.core import ACCOUNT_ID as DEFAULT_ACCOUNT_ID

DEFAULT_SENDER_ID = "AIDAIT2UOQQY3AUEKVGXU"

MAXIMUM_MESSAGE_LENGTH = 262144  # 256 KiB

MAXIMUM_MESSAGE_SIZE_ATTR_LOWER_BOUND = 1024
MAXIMUM_MESSAGE_SIZE_ATTR_UPPER_BOUND = MAXIMUM_MESSAGE_LENGTH

TRANSPORT_TYPE_ENCODINGS = {
    "String": b"\x01",
    "Binary": b"\x02",
    "Number": b"\x01",
    "String.custom": b"\x01",
}

STRING_TYPE_FIELD_INDEX = 1
BINARY_TYPE_FIELD_INDEX = 2
STRING_LIST_TYPE_FIELD_INDEX = 3
BINARY_LIST_TYPE_FIELD_INDEX = 4

# Valid attribute name rules can found at
# https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-message-metadata.html
ATTRIBUTE_NAME_PATTERN = re.compile("^([a-z]|[A-Z]|[0-9]|[_.\\-])+$")

DEDUPLICATION_TIME_IN_SECONDS = 300


class Message(BaseModel):
    def __init__(self, message_id, body, system_attributes=None):
        self.id = message_id
        self._body = body
        self.message_attributes = {}
        self.receipt_handle = None
        self._old_receipt_handles = []
        self.sender_id = DEFAULT_SENDER_ID
        self.sent_timestamp = None
        self.approximate_first_receive_timestamp = None
        self.approximate_receive_count = 0
        self.deduplication_id = None
        self.group_id = None
        self.sequence_number = None
        self.visible_at = 0
        self.delayed_until = 0
        self.system_attributes = system_attributes or {}

    @property
    def body_md5(self):
        md5 = hashlib.md5()
        md5.update(self._body.encode("utf-8"))
        return md5.hexdigest()

    @property
    def attribute_md5(self):

        md5 = hashlib.md5()

        for attrName in sorted(self.message_attributes.keys()):
            self.validate_attribute_name(attrName)
            attrValue = self.message_attributes[attrName]
            # Encode name
            self.update_binary_length_and_value(md5, self.utf8(attrName))
            # Encode type
            self.update_binary_length_and_value(md5, self.utf8(attrValue["data_type"]))

            if attrValue.get("string_value"):
                md5.update(bytearray([STRING_TYPE_FIELD_INDEX]))
                self.update_binary_length_and_value(
                    md5, self.utf8(attrValue.get("string_value"))
                )
            elif attrValue.get("binary_value"):
                md5.update(bytearray([BINARY_TYPE_FIELD_INDEX]))
                decoded_binary_value = base64.b64decode(attrValue.get("binary_value"))
                self.update_binary_length_and_value(md5, decoded_binary_value)
            # string_list_value type is not implemented, reserved for the future use.
            # See https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_MessageAttributeValue.html
            elif len(attrValue["string_list_value"]) > 0:
                md5.update(bytearray([STRING_LIST_TYPE_FIELD_INDEX]))
                for strListMember in attrValue["string_list_value"]:
                    self.update_binary_length_and_value(md5, self.utf8(strListMember))
            # binary_list_value type is not implemented, reserved for the future use.
            # See https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_MessageAttributeValue.html
            elif len(attrValue["binary_list_value"]) > 0:
                md5.update(bytearray([BINARY_LIST_TYPE_FIELD_INDEX]))
                for strListMember in attrValue["binary_list_value"]:
                    decoded_binary_value = base64.b64decode(strListMember)
                    self.update_binary_length_and_value(md5, decoded_binary_value)

        return md5.hexdigest()

    @staticmethod
    def update_binary_length_and_value(md5, value):
        length_bytes = struct.pack("!I".encode("ascii"), len(value))
        md5.update(length_bytes)
        md5.update(value)

    @staticmethod
    def validate_attribute_name(name):
        if not ATTRIBUTE_NAME_PATTERN.match(name):
            raise MessageAttributesInvalid(
                "The message attribute name '{0}' is invalid. "
                "Attribute name can contain A-Z, a-z, 0-9, "
                "underscore (_), hyphen (-), and period (.) characters.".format(name)
            )

    @staticmethod
    def utf8(string):
        if isinstance(string, str):
            return string.encode("utf-8")
        return string

    @property
    def body(self):
        return escape(self._body).replace('"', "&quot;").replace("\r", "&#xD;")

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

        self._old_receipt_handles.append(self.receipt_handle)
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

    @property
    def all_receipt_handles(self):
        return [self.receipt_handle] + self._old_receipt_handles

    def had_receipt_handle(self, receipt_handle):
        """
        Check if this message ever had this receipt_handle in the past
        """
        return receipt_handle in self.all_receipt_handles


class Queue(CloudFormationModel):
    BASE_ATTRIBUTES = [
        "ApproximateNumberOfMessages",
        "ApproximateNumberOfMessagesDelayed",
        "ApproximateNumberOfMessagesNotVisible",
        "CreatedTimestamp",
        "DelaySeconds",
        "LastModifiedTimestamp",
        "MaximumMessageSize",
        "MessageRetentionPeriod",
        "QueueArn",
        "Policy",
        "RedrivePolicy",
        "ReceiveMessageWaitTimeSeconds",
        "VisibilityTimeout",
    ]
    FIFO_ATTRIBUTES = [
        "ContentBasedDeduplication",
        "DeduplicationScope",
        "FifoQueue",
        "FifoThroughputLimit",
    ]
    KMS_ATTRIBUTES = ["KmsDataKeyReusePeriodSeconds", "KmsMasterKeyId"]
    ALLOWED_PERMISSIONS = (
        "*",
        "ChangeMessageVisibility",
        "DeleteMessage",
        "GetQueueAttributes",
        "GetQueueUrl",
        "ListDeadLetterSourceQueues",
        "PurgeQueue",
        "ReceiveMessage",
        "SendMessage",
    )

    def __init__(self, name, region, **kwargs):
        self.name = name
        self.region = region
        self.tags = {}
        self.permissions = {}

        self._messages = []
        self._pending_messages = set()
        self.deleted_messages = set()

        now = unix_time()
        self.created_timestamp = now
        self.queue_arn = "arn:aws:sqs:{0}:{1}:{2}".format(
            self.region, DEFAULT_ACCOUNT_ID, self.name
        )
        self.dead_letter_queue = None

        self.lambda_event_source_mappings = {}

        # default settings for a non fifo queue
        defaults = {
            "ContentBasedDeduplication": "false",
            "DeduplicationScope": "queue",
            "DelaySeconds": 0,
            "FifoQueue": "false",
            "FifoThroughputLimit": "perQueue",
            "KmsDataKeyReusePeriodSeconds": 300,  # five minutes
            "KmsMasterKeyId": None,
            "MaximumMessageSize": MAXIMUM_MESSAGE_LENGTH,
            "MessageRetentionPeriod": 86400 * 4,  # four days
            "Policy": None,
            "ReceiveMessageWaitTimeSeconds": 0,
            "RedrivePolicy": None,
            "VisibilityTimeout": 30,
        }

        defaults.update(kwargs)
        self._set_attributes(defaults, now)

        # Check some conditions
        if self.fifo_queue and not self.name.endswith(".fifo"):
            raise InvalidParameterValue("Queue name must end in .fifo for FIFO queues")
        if (
            self.maximum_message_size < MAXIMUM_MESSAGE_SIZE_ATTR_LOWER_BOUND
            or self.maximum_message_size > MAXIMUM_MESSAGE_SIZE_ATTR_UPPER_BOUND
        ):
            raise InvalidAttributeValue("MaximumMessageSize")

    @property
    def pending_messages(self):
        return self._pending_messages

    @property
    def pending_message_groups(self):
        return set(
            message.group_id
            for message in self._pending_messages
            if message.group_id is not None
        )

    def _set_attributes(self, attributes, now=None):
        if not now:
            now = unix_time()

        integer_fields = (
            "DelaySeconds",
            "KmsDataKeyreusePeriodSeconds",
            "MaximumMessageSize",
            "MessageRetentionPeriod",
            "ReceiveMessageWaitTime",
            "VisibilityTimeout",
        )
        bool_fields = ("ContentBasedDeduplication", "FifoQueue")

        for key, value in attributes.items():
            if key in integer_fields:
                value = int(value)
            if key in bool_fields:
                value = value == "true"

            if key in ["Policy", "RedrivePolicy"] and value is not None:
                continue

            setattr(self, camelcase_to_underscores(key), value)

        if attributes.get("RedrivePolicy", None) is not None:
            self._setup_dlq(attributes["RedrivePolicy"])

        self.policy = attributes.get("Policy")

        self.last_modified_timestamp = now

    @staticmethod
    def _is_empty_redrive_policy(policy):
        if isinstance(policy, str):
            if policy == "" or len(json.loads(policy)) == 0:
                return True
        elif isinstance(policy, dict) and len(policy) == 0:
            return True

        return False

    def _setup_dlq(self, policy):
        if Queue._is_empty_redrive_policy(policy):
            self.redrive_policy = None
            self.dead_letter_queue = None
            return

        if isinstance(policy, str):
            try:
                self.redrive_policy = json.loads(policy)
            except ValueError:
                raise RESTError(
                    "InvalidParameterValue",
                    "Redrive policy is not a dict or valid json",
                )
        elif isinstance(policy, dict):
            self.redrive_policy = policy
        else:
            raise RESTError(
                "InvalidParameterValue", "Redrive policy is not a dict or valid json"
            )

        if "deadLetterTargetArn" not in self.redrive_policy:
            raise RESTError(
                "InvalidParameterValue",
                "Redrive policy does not contain deadLetterTargetArn",
            )
        if "maxReceiveCount" not in self.redrive_policy:
            raise RESTError(
                "InvalidParameterValue",
                "Redrive policy does not contain maxReceiveCount",
            )

        # 'maxReceiveCount' is stored as int
        self.redrive_policy["maxReceiveCount"] = int(
            self.redrive_policy["maxReceiveCount"]
        )

        for queue in sqs_backends[self.region].queues.values():
            if queue.queue_arn == self.redrive_policy["deadLetterTargetArn"]:
                self.dead_letter_queue = queue

                if self.fifo_queue and not queue.fifo_queue:
                    raise RESTError(
                        "InvalidParameterCombination",
                        "Fifo queues cannot use non fifo dead letter queues",
                    )
                break
        else:
            raise RESTError(
                "AWS.SimpleQueueService.NonExistentQueue",
                "Could not find DLQ for {0}".format(
                    self.redrive_policy["deadLetterTargetArn"]
                ),
            )

    @staticmethod
    def cloudformation_name_type():
        return "QueueName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sqs-queue.html
        return "AWS::SQS::Queue"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = deepcopy(cloudformation_json["Properties"])
        # remove Tags from properties and convert tags list to dict
        tags = properties.pop("Tags", [])
        tags_dict = tags_from_cloudformation_tags_list(tags)

        # Could be passed as an integer - just treat it as a string
        resource_name = str(resource_name)

        sqs_backend = sqs_backends[region_name]
        return sqs_backend.create_queue(
            name=resource_name, tags=tags_dict, region=region_name, **properties
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        queue_name = original_resource.name

        sqs_backend = sqs_backends[region_name]
        queue = sqs_backend.get_queue(queue_name)
        if "VisibilityTimeout" in properties:
            queue.visibility_timeout = int(properties["VisibilityTimeout"])

        if "ReceiveMessageWaitTimeSeconds" in properties:
            queue.receive_message_wait_time_seconds = int(
                properties["ReceiveMessageWaitTimeSeconds"]
            )
        return queue

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        sqs_backend = sqs_backends[region_name]
        sqs_backend.delete_queue(resource_name)

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

        for attribute in self.BASE_ATTRIBUTES:
            attr = getattr(self, camelcase_to_underscores(attribute))
            result[attribute] = attr

        if self.fifo_queue:
            for attribute in self.FIFO_ATTRIBUTES:
                attr = getattr(self, camelcase_to_underscores(attribute))
                result[attribute] = attr

        if self.kms_master_key_id:
            for attribute in self.KMS_ATTRIBUTES:
                attr = getattr(self, camelcase_to_underscores(attribute))
                result[attribute] = attr

        if self.policy:
            result["Policy"] = self.policy

        if self.redrive_policy:
            result["RedrivePolicy"] = json.dumps(self.redrive_policy)

        for key in result:
            if isinstance(result[key], bool):
                result[key] = str(result[key]).lower()

        return result

    def url(self, request_url):
        return "{0}://{1}/{2}/{3}".format(
            request_url.scheme, request_url.netloc, DEFAULT_ACCOUNT_ID, self.name
        )

    @property
    def messages(self):
        # TODO: This can become very inefficient if a large number of messages are in-flight
        return [
            message
            for message in self._messages
            if message.visible and not message.delayed
        ]

    def add_message(self, message):
        if (
            self.fifo_queue
            and self.attributes.get("ContentBasedDeduplication") == "true"
        ):
            for m in self._messages:
                if m.deduplication_id == message.deduplication_id:
                    diff = message.sent_timestamp - m.sent_timestamp
                    # if a duplicate message is received within the deduplication time then it should
                    # not be added to the queue
                    if diff / 1000 < DEDUPLICATION_TIME_IN_SECONDS:
                        return

        self._messages.append(message)

        for arn, esm in self.lambda_event_source_mappings.items():
            backend = sqs_backends[self.region]

            """
            Lambda polls the queue and invokes your function synchronously with an event
            that contains queue messages. Lambda reads messages in batches and invokes
            your function once for each batch. When your function successfully processes
            a batch, Lambda deletes its messages from the queue.
            """
            messages = backend.receive_messages(
                self.name,
                esm.batch_size,
                self.receive_message_wait_time_seconds,
                self.visibility_timeout,
            )

            from moto.awslambda import lambda_backends

            result = lambda_backends[self.region].send_sqs_batch(
                arn, messages, self.queue_arn
            )

            if result:
                [backend.delete_message(self.name, m.receipt_handle) for m in messages]
            else:
                # Make messages visible again
                [
                    backend.change_message_visibility(
                        self.name, m.receipt_handle, visibility_timeout=0
                    )
                    for m in messages
                ]

    def delete_message(self, receipt_handle):
        if receipt_handle in self.deleted_messages:
            # Already deleted - gracefully handle deleting it again
            return

        if not any(
            message.had_receipt_handle(receipt_handle) for message in self._messages
        ):
            raise ReceiptHandleIsInvalid()

        # Delete message from queue regardless of pending state
        new_messages = []
        for message in self._messages:
            if message.had_receipt_handle(receipt_handle):
                self.pending_messages.discard(message)
                self.deleted_messages.update(message.all_receipt_handles)
                continue
            new_messages.append(message)
        self._messages = new_messages

    @classmethod
    def has_cfn_attr(cls, attribute_name):
        return attribute_name in ["Arn", "QueueName"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.queue_arn
        elif attribute_name == "QueueName":
            return self.name
        raise UnformattedGetAttTemplateException()

    @property
    def policy(self):
        if self._policy_json.get("Statement"):
            return json.dumps(self._policy_json)
        else:
            return None

    @policy.setter
    def policy(self, policy):
        if policy:
            self._policy_json = json.loads(policy)
        else:
            self._policy_json = {
                "Version": "2012-10-17",
                "Id": "{}/SQSDefaultPolicy".format(self.queue_arn),
                "Statement": [],
            }


def _filter_message_attributes(message, input_message_attributes):
    filtered_message_attributes = {}
    return_all = "All" in input_message_attributes
    for key, value in message.message_attributes.items():
        if return_all or key in input_message_attributes:
            filtered_message_attributes[key] = value
    message.message_attributes = filtered_message_attributes


class SQSBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.queues: Dict[str, Queue] = {}
        super().__init__()

    def reset(self):
        region_name = self.region_name
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "sqs"
        )

    def create_queue(self, name, tags=None, **kwargs):
        queue = self.queues.get(name)
        if queue:
            try:
                kwargs.pop("region")
            except KeyError:
                pass

            new_queue = Queue(name, region=self.region_name, **kwargs)

            queue_attributes = queue.attributes
            new_queue_attributes = new_queue.attributes

            # only the attributes which are being sent for the queue
            # creation have to be compared if the queue is existing.
            for key in kwargs:
                if queue_attributes.get(key) != new_queue_attributes.get(key):
                    raise QueueAlreadyExists("The specified queue already exists.")
        else:
            try:
                kwargs.pop("region")
            except KeyError:
                pass
            queue = Queue(name, region=self.region_name, **kwargs)
            self.queues[name] = queue

        if tags:
            queue.tags = tags

        return queue

    def get_queue_url(self, queue_name):
        return self.get_queue(queue_name)

    def list_queues(self, queue_name_prefix):
        re_str = ".*"
        if queue_name_prefix:
            re_str = "^{0}.*".format(queue_name_prefix)
        prefix_re = re.compile(re_str)
        qs = []
        for name, q in self.queues.items():
            if prefix_re.search(name):
                qs.append(q)
        return qs[:1000]

    def get_queue(self, queue_name):
        queue = self.queues.get(queue_name)
        if queue is None:
            raise QueueDoesNotExist()
        return queue

    def delete_queue(self, queue_name):
        self.get_queue(queue_name)

        del self.queues[queue_name]

    def get_queue_attributes(self, queue_name, attribute_names):
        queue = self.get_queue(queue_name)
        if not attribute_names:
            return {}

        valid_names = (
            ["All"]
            + queue.BASE_ATTRIBUTES
            + queue.FIFO_ATTRIBUTES
            + queue.KMS_ATTRIBUTES
        )
        invalid_name = next(
            (name for name in attribute_names if name not in valid_names), None
        )

        if invalid_name or invalid_name == "":
            raise InvalidAttributeName(invalid_name)

        attributes = {}

        if "All" in attribute_names:
            attributes = queue.attributes
        else:
            for name in (name for name in attribute_names if name in queue.attributes):
                if queue.attributes.get(name) is not None:
                    attributes[name] = queue.attributes.get(name)

        return attributes

    def set_queue_attributes(self, queue_name, attributes):
        queue = self.get_queue(queue_name)
        queue._set_attributes(attributes)
        return queue

    def send_message(
        self,
        queue_name,
        message_body,
        message_attributes=None,
        delay_seconds=None,
        deduplication_id=None,
        group_id=None,
        system_attributes=None,
    ):

        queue = self.get_queue(queue_name)

        if len(message_body) > queue.maximum_message_size:
            msg = "One or more parameters are invalid. Reason: Message must be shorter than {} bytes.".format(
                queue.maximum_message_size
            )
            raise InvalidParameterValue(msg)

        if delay_seconds:
            delay_seconds = int(delay_seconds)
        else:
            delay_seconds = queue.delay_seconds

        message_id = get_random_message_id()
        message = Message(message_id, message_body, system_attributes)

        # if content based deduplication is set then set sha256 hash of the message
        # as the deduplication_id
        if queue.attributes.get("ContentBasedDeduplication") == "true":
            sha256 = hashlib.sha256()
            sha256.update(message_body.encode("utf-8"))
            message.deduplication_id = sha256.hexdigest()

        # Attributes, but not *message* attributes
        if deduplication_id is not None:
            message.deduplication_id = deduplication_id
            message.sequence_number = "".join(
                random.choice(string.digits) for _ in range(20)
            )

        if group_id is None:
            # MessageGroupId is a mandatory parameter for all
            # messages in a fifo queue
            if queue.fifo_queue:
                raise MissingParameter("MessageGroupId")
        else:
            if not queue.fifo_queue:
                msg = (
                    "Value {} for parameter MessageGroupId is invalid. "
                    "Reason: The request include parameter that is not valid for this queue type."
                ).format(group_id)
                raise InvalidParameterValue(msg)
            message.group_id = group_id

        if message_attributes:
            message.message_attributes = message_attributes

        message.mark_sent(delay_seconds=delay_seconds)

        queue.add_message(message)

        return message

    def send_message_batch(self, queue_name, entries):
        self.get_queue(queue_name)

        if any(
            not re.match(r"^[\w-]{1,80}$", entry["Id"]) for entry in entries.values()
        ):
            raise InvalidBatchEntryId()

        body_length = next(
            (
                len(entry["MessageBody"])
                for entry in entries.values()
                if len(entry["MessageBody"]) > MAXIMUM_MESSAGE_LENGTH
            ),
            False,
        )
        if body_length:
            raise BatchRequestTooLong(body_length)

        duplicate_id = self._get_first_duplicate_id(
            [entry["Id"] for entry in entries.values()]
        )
        if duplicate_id:
            raise BatchEntryIdsNotDistinct(duplicate_id)

        if len(entries) > 10:
            raise TooManyEntriesInBatchRequest(len(entries))

        messages = []
        for entry in entries.values():
            # Loop through looking for messages
            message = self.send_message(
                queue_name,
                entry["MessageBody"],
                message_attributes=entry["MessageAttributes"],
                delay_seconds=entry["DelaySeconds"],
                group_id=entry.get("MessageGroupId"),
                deduplication_id=entry.get("MessageDeduplicationId"),
            )
            message.user_id = entry["Id"]

            messages.append(message)

        return messages

    def _get_first_duplicate_id(self, ids):
        unique_ids = set()
        for _id in ids:
            if _id in unique_ids:
                return _id
            unique_ids.add(_id)
        return None

    def receive_messages(
        self,
        queue_name,
        count,
        wait_seconds_timeout,
        visibility_timeout,
        message_attribute_names=None,
    ):
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
        if message_attribute_names is None:
            message_attribute_names = []
        queue = self.get_queue(queue_name)
        result = []
        previous_result_count = len(result)

        polling_end = unix_time() + wait_seconds_timeout
        currently_pending_groups = deepcopy(queue.pending_message_groups)

        # queue.messages only contains visible messages
        while True:

            if result or (wait_seconds_timeout and unix_time() > polling_end):
                break

            messages_to_dlq = []

            for message in queue.messages:
                if not message.visible:
                    continue

                if message in queue.pending_messages:
                    # The message is pending but is visible again, so the
                    # consumer must have timed out.
                    queue.pending_messages.remove(message)
                    currently_pending_groups = deepcopy(queue.pending_message_groups)

                if message.group_id and queue.fifo_queue:
                    if message.group_id in currently_pending_groups:
                        # A previous call is still processing messages in this group, so we cannot deliver this one.
                        continue

                if (
                    queue.dead_letter_queue is not None
                    and queue.redrive_policy
                    and message.approximate_receive_count
                    >= queue.redrive_policy["maxReceiveCount"]
                ):
                    messages_to_dlq.append(message)
                    continue

                queue.pending_messages.add(message)
                message.mark_received(visibility_timeout=visibility_timeout)
                # Create deepcopy to not mutate the message state when filtering for attributes
                message_copy = deepcopy(message)
                _filter_message_attributes(message_copy, message_attribute_names)
                if not self.is_message_valid_based_on_retention_period(
                    queue_name, message
                ):
                    break
                result.append(message_copy)
                if len(result) >= count:
                    break

            for message in messages_to_dlq:
                queue._messages.remove(message)
                queue.dead_letter_queue.add_message(message)

            if previous_result_count == len(result):
                if wait_seconds_timeout == 0:
                    # There is timeout and we have added no additional results,
                    # so break to avoid an infinite loop.
                    break

                import time

                time.sleep(0.01)
                continue

            previous_result_count = len(result)

        return result

    def delete_message(self, queue_name, receipt_handle):
        queue = self.get_queue(queue_name)

        queue.delete_message(receipt_handle)

    def change_message_visibility(self, queue_name, receipt_handle, visibility_timeout):
        queue = self.get_queue(queue_name)
        for message in queue._messages:
            if message.had_receipt_handle(receipt_handle):

                visibility_timeout_msec = int(visibility_timeout) * 1000
                given_visibility_timeout = unix_time_millis() + visibility_timeout_msec
                if given_visibility_timeout - message.sent_timestamp > 43200 * 1000:
                    raise InvalidParameterValue(
                        "Value {0} for parameter VisibilityTimeout is invalid. Reason: Total "
                        "VisibilityTimeout for the message is beyond the limit [43200 seconds]".format(
                            visibility_timeout
                        )
                    )

                message.change_visibility(visibility_timeout)
                if message.visible and message in queue.pending_messages:
                    # If the message is visible again, remove it from pending
                    # messages.
                    queue.pending_messages.remove(message)
                return
        raise ReceiptHandleIsInvalid

    def purge_queue(self, queue_name):
        queue = self.get_queue(queue_name)
        queue._messages = []
        queue._pending_messages = set()

    def list_dead_letter_source_queues(self, queue_name):
        dlq = self.get_queue(queue_name)

        queues = []
        for queue in self.queues.values():
            if queue.dead_letter_queue is dlq:
                queues.append(queue)

        return queues

    def add_permission(self, queue_name, actions, account_ids, label):
        queue = self.get_queue(queue_name)

        if not actions:
            raise MissingParameter("Actions")

        if not account_ids:
            raise InvalidParameterValue(
                "Value [] for parameter PrincipalId is invalid. Reason: Unable to verify."
            )

        count = len(actions)
        if count > 7:
            raise OverLimit(count)

        invalid_action = next(
            (action for action in actions if action not in Queue.ALLOWED_PERMISSIONS),
            None,
        )
        if invalid_action:
            raise InvalidParameterValue(
                "Value SQS:{} for parameter ActionName is invalid. "
                "Reason: Only the queue owner is allowed to invoke this action.".format(
                    invalid_action
                )
            )

        policy = queue._policy_json
        statement = next(
            (
                statement
                for statement in policy["Statement"]
                if statement["Sid"] == label
            ),
            None,
        )
        if statement:
            raise InvalidParameterValue(
                "Value {} for parameter Label is invalid. "
                "Reason: Already exists.".format(label)
            )

        principals = [
            "arn:aws:iam::{}:root".format(account_id) for account_id in account_ids
        ]
        actions = ["SQS:{}".format(action) for action in actions]

        statement = {
            "Sid": label,
            "Effect": "Allow",
            "Principal": {"AWS": principals[0] if len(principals) == 1 else principals},
            "Action": actions[0] if len(actions) == 1 else actions,
            "Resource": queue.queue_arn,
        }

        queue._policy_json["Statement"].append(statement)

    def remove_permission(self, queue_name, label):
        queue = self.get_queue(queue_name)

        statements = queue._policy_json["Statement"]
        statements_new = [
            statement for statement in statements if statement["Sid"] != label
        ]

        if len(statements) == len(statements_new):
            raise InvalidParameterValue(
                "Value {} for parameter Label is invalid. "
                "Reason: can't find label on existing policy.".format(label)
            )

        queue._policy_json["Statement"] = statements_new

    def tag_queue(self, queue_name, tags):
        queue = self.get_queue(queue_name)

        if not len(tags):
            raise MissingParameter("Tags")

        if len(tags) > 50:
            raise InvalidParameterValue(
                "Too many tags added for queue {}.".format(queue_name)
            )

        queue.tags.update(tags)

    def untag_queue(self, queue_name, tag_keys):
        queue = self.get_queue(queue_name)

        if not len(tag_keys):
            raise RESTError(
                "InvalidParameterValue",
                "Tag keys must be between 1 and 128 characters in length.",
            )

        for key in tag_keys:
            try:
                del queue.tags[key]
            except KeyError:
                pass

    def list_queue_tags(self, queue_name):
        return self.get_queue(queue_name)

    def is_message_valid_based_on_retention_period(self, queue_name, message):
        message_attributes = self.get_queue_attributes(
            queue_name, ["MessageRetentionPeriod"]
        )
        retain_until = (
            message_attributes.get("MessageRetentionPeriod")
            + message.sent_timestamp / 1000
        )
        if retain_until <= unix_time():
            return False
        return True


sqs_backends = BackendDict(SQSBackend, "sqs")
