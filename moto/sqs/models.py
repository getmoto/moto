from __future__ import unicode_literals

import base64
import hashlib
import json
import re
import six
import struct
from copy import deepcopy
from xml.sax.saxutils import escape

from boto3 import Session

from moto.core.exceptions import RESTError
from moto.core import BaseBackend, BaseModel
from moto.core.utils import (
    camelcase_to_underscores,
    get_random_message_id,
    unix_time,
    unix_time_millis,
)
from .utils import generate_receipt_handle
from .exceptions import (
    MessageAttributesInvalid,
    MessageNotInflight,
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
)

from moto.core import ACCOUNT_ID as DEFAULT_ACCOUNT_ID

DEFAULT_SENDER_ID = "AIDAIT2UOQQY3AUEKVGXU"

MAXIMUM_MESSAGE_LENGTH = 262144  # 256 KiB

TRANSPORT_TYPE_ENCODINGS = {"String": b"\x01", "Binary": b"\x02", "Number": b"\x01"}


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
        self.deduplication_id = None
        self.group_id = None
        self.visible_at = 0
        self.delayed_until = 0

    @property
    def body_md5(self):
        md5 = hashlib.md5()
        md5.update(self._body.encode("utf-8"))
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
                return str.encode("utf-8")
            return str

        md5 = hashlib.md5()
        struct_format = "!I".encode("ascii")  # ensure it's a bytestring
        for name in sorted(self.message_attributes.keys()):
            attr = self.message_attributes[name]
            data_type = attr["data_type"]

            encoded = utf8("")
            # Each part of each attribute is encoded right after it's
            # own length is packed into a 4-byte integer
            # 'timestamp' -> b'\x00\x00\x00\t'
            encoded += struct.pack(struct_format, len(utf8(name))) + utf8(name)
            # The datatype is additionally given a final byte
            # representing which type it is
            encoded += struct.pack(struct_format, len(data_type)) + utf8(data_type)
            encoded += TRANSPORT_TYPE_ENCODINGS[data_type]

            if data_type == "String" or data_type == "Number":
                value = attr["string_value"]
            elif data_type == "Binary":
                value = base64.b64decode(attr["binary_value"])
            else:
                print(
                    "Moto hasn't implemented MD5 hashing for {} attributes".format(
                        data_type
                    )
                )
                # The following should be enough of a clue to users that
                # they are not, in fact, looking at a correct MD5 while
                # also following the character and length constraints of
                # MD5 so as not to break client softwre
                return "deadbeefdeadbeefdeadbeefdeadbeef"

            encoded += struct.pack(struct_format, len(utf8(value))) + utf8(value)

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
    FIFO_ATTRIBUTES = ["FifoQueue", "ContentBasedDeduplication"]
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
            "DelaySeconds": 0,
            "FifoQueue": "false",
            "KmsDataKeyReusePeriodSeconds": 300,  # five minutes
            "KmsMasterKeyId": None,
            "MaximumMessageSize": int(64 << 12),
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
            raise MessageAttributesInvalid(
                "Queue name must end in .fifo for FIFO queues"
            )

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

        for key, value in six.iteritems(attributes):
            if key in integer_fields:
                value = int(value)
            if key in bool_fields:
                value = value == "true"

            if key in ["Policy", "RedrivePolicy"] and value is not None:
                continue

            setattr(self, camelcase_to_underscores(key), value)

        if attributes.get("RedrivePolicy", None):
            self._setup_dlq(attributes["RedrivePolicy"])

        if attributes.get("Policy"):
            self.policy = attributes["Policy"]

        self.last_modified_timestamp = now

    def _setup_dlq(self, policy):

        if isinstance(policy, six.text_type):
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

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        sqs_backend = sqs_backends[region_name]
        return sqs_backend.create_queue(
            name=properties["QueueName"], region=region_name, **properties
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        queue_name = properties["QueueName"]

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
        properties = cloudformation_json["Properties"]
        queue_name = properties["QueueName"]
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
        return [
            message
            for message in self._messages
            if message.visible and not message.delayed
        ]

    def add_message(self, message):
        self._messages.append(message)
        from moto.awslambda import lambda_backends

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

            result = lambda_backends[self.region].send_sqs_batch(
                arn, messages, self.queue_arn
            )

            if result:
                [backend.delete_message(self.name, m.receipt_handle) for m in messages]
            else:
                [
                    backend.change_message_visibility(self.name, m.receipt_handle, 0)
                    for m in messages
                ]

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


class SQSBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.queues = {}
        super(SQSBackend, self).__init__()

    def reset(self):
        region_name = self.region_name
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name)

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
            static_attributes = (
                "DelaySeconds",
                "MaximumMessageSize",
                "MessageRetentionPeriod",
                "Policy",
                "QueueArn",
                "ReceiveMessageWaitTimeSeconds",
                "RedrivePolicy",
                "VisibilityTimeout",
                "KmsMasterKeyId",
                "KmsDataKeyReusePeriodSeconds",
                "FifoQueue",
                "ContentBasedDeduplication",
            )

            for key in static_attributes:
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
        if queue_name in self.queues:
            return self.queues.pop(queue_name)
        return False

    def get_queue_attributes(self, queue_name, attribute_names):
        queue = self.get_queue(queue_name)

        if not len(attribute_names):
            attribute_names.append("All")

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
    ):

        queue = self.get_queue(queue_name)

        if delay_seconds:
            delay_seconds = int(delay_seconds)
        else:
            delay_seconds = queue.delay_seconds

        message_id = get_random_message_id()
        message = Message(message_id, message_body)

        # Attributes, but not *message* attributes
        if deduplication_id is not None:
            message.deduplication_id = deduplication_id
        if group_id is not None:
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
        for index, entry in entries.items():
            # Loop through looking for messages
            message = self.send_message(
                queue_name,
                entry["MessageBody"],
                message_attributes=entry["MessageAttributes"],
                delay_seconds=entry["DelaySeconds"],
            )
            message.user_id = entry["Id"]

            messages.append(message)

        return messages

    def _get_first_duplicate_id(self, ids):
        unique_ids = set()
        for id in ids:
            if id in unique_ids:
                return id
            unique_ids.add(id)
        return None

    def receive_messages(
        self, queue_name, count, wait_seconds_timeout, visibility_timeout
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

                queue.pending_messages.add(message)

                if (
                    queue.dead_letter_queue is not None
                    and message.approximate_receive_count
                    >= queue.redrive_policy["maxReceiveCount"]
                ):
                    messages_to_dlq.append(message)
                    continue

                message.mark_received(visibility_timeout=visibility_timeout)
                result.append(message)
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

        if not any(
            message.receipt_handle == receipt_handle for message in queue._messages
        ):
            raise ReceiptHandleIsInvalid()

        new_messages = []
        for message in queue._messages:
            # Only delete message if it is not visible and the receipt_handle
            # matches.
            if message.receipt_handle == receipt_handle:
                queue.pending_messages.remove(message)
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
                if message.visible:
                    # If the message is visible again, remove it from pending
                    # messages.
                    queue.pending_messages.remove(message)
                return
        raise ReceiptHandleIsInvalid

    def purge_queue(self, queue_name):
        queue = self.get_queue(queue_name)
        queue._messages = []

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
            raise MissingParameter()

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
            raise RESTError(
                "MissingParameter", "The request must contain the parameter Tags."
            )

        if len(tags) > 50:
            raise RESTError(
                "InvalidParameterValue",
                "Too many tags added for queue {}.".format(queue_name),
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


sqs_backends = {}
for region in Session().get_available_regions("sqs"):
    sqs_backends[region] = SQSBackend(region)
for region in Session().get_available_regions("sqs", partition_name="aws-us-gov"):
    sqs_backends[region] = SQSBackend(region)
for region in Session().get_available_regions("sqs", partition_name="aws-cn"):
    sqs_backends[region] = SQSBackend(region)
