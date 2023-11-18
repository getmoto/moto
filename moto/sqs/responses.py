import json
import re

from moto.core.exceptions import RESTError, JsonRESTError
from moto.core.responses import BaseResponse
from moto.core.utils import (
    amz_crc32,
    amzn_request_id,
    underscores_to_camelcase,
    camelcase_to_underscores,
    camelcase_to_pascal,
)
from moto.utilities.constants import JSON_TYPES
from functools import wraps
from urllib.parse import urlparse

from .exceptions import (
    EmptyBatchRequest,
    InvalidAttributeName,
    ReceiptHandleIsInvalid,
    BatchEntryIdsNotDistinct,
)
from .models import sqs_backends
from .utils import (
    parse_message_attributes,
    extract_input_message_attributes,
    validate_message_attributes,
)

MAXIMUM_VISIBILTY_TIMEOUT = 43200
MAXIMUM_MESSAGE_LENGTH = 262144  # 256 KiB
DEFAULT_RECEIVED_MESSAGES = 1


def jsonify_error(method):
    """
    The decorator to convert an RESTError to JSON, if necessary
    """

    @wraps(method)
    def f(self: "SQSResponse"):
        try:
            return method(self)
        except RESTError as e:
            if self.is_json():
                raise e.to_json()
            raise e

    return f


class SQSResponse(BaseResponse):

    region_regex = re.compile(r"://(.+?)\.queue\.amazonaws\.com")

    def is_json(self) -> bool:
        """
        botocore 1.29.127 changed the wire-format to SQS
        This means three things:
         - The Content-Type is set to JSON
         - The input-parameters are in different formats
         - The output is in a different format
         The change has been reverted for now, but it will be re-introduced later:
         https://github.com/boto/botocore/pull/2931
        """
        return self.headers.get("Content-Type") in JSON_TYPES

    @property
    def sqs_backend(self):
        return sqs_backends[self.region]

    @property
    def attribute(self):
        try:
            assert self.is_json()
            return json.loads(self.body).get("Attributes", {})
        except:  # noqa: E722 Do not use bare except
            if not hasattr(self, "_attribute"):
                self._attribute = self._get_map_prefix(
                    "Attribute", key_end=".Name", value_end=".Value"
                )
        return self._attribute

    @property
    def tags(self):
        if not hasattr(self, "_tags"):
            if self.is_json():
                self._tags = self._get_param("tags")
            else:
                self._tags = self._get_map_prefix(
                    "Tag", key_end=".Key", value_end=".Value"
                )
        return self._tags

    def _get_queue_name(self):
        try:
            if self.is_json():
                queue_url = self._get_param("QueueUrl")
            else:
                queue_url = self.querystring.get("QueueUrl")[0]
            if queue_url.startswith("http://") or queue_url.startswith("https://"):
                return queue_url.split("/")[-1]
            else:
                # The parameter could be the name itself, which AWS also accepts
                return queue_url
        except TypeError:
            # Fallback to reading from the URL for botocore
            return self.path.split("/")[-1]

    def _get_validated_visibility_timeout(self, timeout=None):
        """
        :raises ValueError: If specified visibility timeout exceeds MAXIMUM_VISIBILTY_TIMEOUT
        :raises TypeError: If visibility timeout was not specified
        """
        if timeout is not None:
            visibility_timeout = int(timeout)
        else:
            if self.is_json():
                visibility_timeout = self._get_param("VisibilityTimeout")
            else:
                visibility_timeout = int(self.querystring.get("VisibilityTimeout")[0])

        if visibility_timeout > MAXIMUM_VISIBILTY_TIMEOUT:
            raise ValueError

        return visibility_timeout

    @amz_crc32  # crc last as request_id can edit XML
    @amzn_request_id
    def call_action(self):
        status_code, headers, body = super().call_action()
        if status_code == 404:
            queue_name = self.querystring.get("QueueName", [""])[0]
            template = self.response_template(ERROR_INEXISTENT_QUEUE)
            response = template.render(queue_name=queue_name)
            return 404, headers, response
        return status_code, headers, body

    def _error(self, code, message, status=400):
        if self.is_json():
            err = JsonRESTError(error_type=code, message=message)
            err.code = status
            raise err
        template = self.response_template(ERROR_TEMPLATE)
        return status, {"status": status}, template.render(code=code, message=message)

    @jsonify_error
    def create_queue(self):
        request_url = urlparse(self.uri)
        queue_name = self._get_param("QueueName")

        queue = self.sqs_backend.create_queue(queue_name, self.tags, **self.attribute)

        if self.is_json():
            return json.dumps({"QueueUrl": queue.url(request_url)})

        template = self.response_template(CREATE_QUEUE_RESPONSE)
        return template.render(queue_url=queue.url(request_url))

    @jsonify_error
    def get_queue_url(self):
        request_url = urlparse(self.uri)
        queue_name = self._get_param("QueueName")

        queue = self.sqs_backend.get_queue_url(queue_name)

        if self.is_json():
            return json.dumps({"QueueUrl": queue.url(request_url)})

        template = self.response_template(GET_QUEUE_URL_RESPONSE)
        return template.render(queue_url=queue.url(request_url))

    @jsonify_error
    def list_queues(self):
        request_url = urlparse(self.uri)
        queue_name_prefix = self._get_param("QueueNamePrefix")
        queues = self.sqs_backend.list_queues(queue_name_prefix)

        if self.is_json():
            if queues:
                return json.dumps(
                    {"QueueUrls": [queue.url(request_url) for queue in queues]}
                )
            else:
                return "{}"

        template = self.response_template(LIST_QUEUES_RESPONSE)
        return template.render(queues=queues, request_url=request_url)

    @jsonify_error
    def change_message_visibility(self):
        queue_name = self._get_queue_name()
        receipt_handle = self._get_param("ReceiptHandle")

        try:
            visibility_timeout = self._get_validated_visibility_timeout()
        except ValueError:
            return 400, {}, ERROR_MAX_VISIBILITY_TIMEOUT_RESPONSE

        self.sqs_backend.change_message_visibility(
            queue_name=queue_name,
            receipt_handle=receipt_handle,
            visibility_timeout=visibility_timeout,
        )

        if self.is_json():
            return "{}"

        template = self.response_template(CHANGE_MESSAGE_VISIBILITY_RESPONSE)
        return template.render()

    def change_message_visibility_batch(self):
        queue_name = self._get_queue_name()
        if self.is_json():
            entries = [
                {camelcase_to_underscores(key): value for key, value in entr.items()}
                for entr in self._get_param("Entries")
            ]
        else:
            entries = self._get_list_prefix("ChangeMessageVisibilityBatchRequestEntry")

        success = []
        error = []
        for entry in entries:
            try:
                visibility_timeout = self._get_validated_visibility_timeout(
                    entry["visibility_timeout"]
                )
            except ValueError:
                error.append(
                    {
                        "Id": entry["id"],
                        "SenderFault": "true",
                        "Code": "InvalidParameterValue",
                        "Message": "Visibility timeout invalid",
                    }
                )
                continue

            try:
                self.sqs_backend.change_message_visibility(
                    queue_name=queue_name,
                    receipt_handle=entry["receipt_handle"],
                    visibility_timeout=visibility_timeout,
                )
                success.append(entry["id"])
            except ReceiptHandleIsInvalid as e:
                error.append(
                    {
                        "Id": entry["id"],
                        "SenderFault": "true",
                        "Code": "ReceiptHandleIsInvalid",
                        "Message": e.description,
                    }
                )

        if self.is_json():
            return json.dumps(
                {"Successful": [{"Id": _id} for _id in success], "Failed": error}
            )

        template = self.response_template(CHANGE_MESSAGE_VISIBILITY_BATCH_RESPONSE)
        return template.render(success=success, errors=error)

    @jsonify_error
    def get_queue_attributes(self):
        queue_name = self._get_queue_name()

        if not self.is_json() and self.querystring.get("AttributeNames"):
            raise InvalidAttributeName("")

        if self.is_json():
            attribute_names = self._get_param("AttributeNames")
            if attribute_names == [] or (attribute_names and "" in attribute_names):
                raise InvalidAttributeName("")
        else:
            # if connecting to AWS via boto, then 'AttributeName' is just a normal parameter
            attribute_names = self._get_multi_param(
                "AttributeName"
            ) or self.querystring.get("AttributeName")

        attributes = self.sqs_backend.get_queue_attributes(queue_name, attribute_names)

        if self.is_json():
            if len(attributes) == 0:
                return "{}"
            return json.dumps(
                {
                    "Attributes": {
                        key: str(value)
                        for key, value in attributes.items()
                        if value is not None
                    }
                }
            )

        template = self.response_template(GET_QUEUE_ATTRIBUTES_RESPONSE)
        return template.render(attributes=attributes)

    @jsonify_error
    def set_queue_attributes(self):
        # TODO validate self.get_param('QueueUrl')
        attribute = self.attribute

        # Fixes issue with Policy set to empty str
        attribute_names = self._get_multi_param("Attribute")
        if attribute_names:
            for attr in attribute_names:
                if attr["Name"] == "Policy" and len(attr["Value"]) == 0:
                    attribute = {attr["Name"]: None}

        queue_name = self._get_queue_name()
        self.sqs_backend.set_queue_attributes(queue_name, attribute)

        return SET_QUEUE_ATTRIBUTE_RESPONSE

    @jsonify_error
    def delete_queue(self):
        # TODO validate self.get_param('QueueUrl')
        queue_name = self._get_queue_name()

        self.sqs_backend.delete_queue(queue_name)

        template = self.response_template(DELETE_QUEUE_RESPONSE)
        return template.render()

    @jsonify_error
    def send_message(self):
        message = self._get_param("MessageBody")
        delay_seconds = int(self._get_param("DelaySeconds", 0))
        message_group_id = self._get_param("MessageGroupId")
        message_dedupe_id = self._get_param("MessageDeduplicationId")

        if len(message) > MAXIMUM_MESSAGE_LENGTH:
            return self._error(
                "InvalidParameterValue",
                message="One or more parameters are invalid. Reason: Message must be shorter than 262144 bytes.",
            )

        if self.is_json():
            message_attributes = self._get_param("MessageAttributes")
            self.normalize_json_msg_attributes(message_attributes)
        else:
            message_attributes = parse_message_attributes(self.querystring)

        if self.is_json():
            system_message_attributes = self._get_param("MessageSystemAttributes")
            self.normalize_json_msg_attributes(system_message_attributes)
        else:
            system_message_attributes = parse_message_attributes(
                self.querystring, key="MessageSystemAttribute"
            )

        queue_name = self._get_queue_name()

        try:
            message = self.sqs_backend.send_message(
                queue_name,
                message,
                message_attributes=message_attributes,
                delay_seconds=delay_seconds,
                deduplication_id=message_dedupe_id,
                group_id=message_group_id,
                system_attributes=system_message_attributes,
            )
        except RESTError as err:
            return self._error(err.error_type, err.message)

        if self.is_json():
            resp = {"MD5OfMessageBody": message.body_md5, "MessageId": message.id}
            if len(message.message_attributes) > 0:
                resp["MD5OfMessageAttributes"] = message.attribute_md5
            return json.dumps(resp)

        template = self.response_template(SEND_MESSAGE_RESPONSE)
        return template.render(message=message, message_attributes=message_attributes)

    def normalize_json_msg_attributes(self, message_attributes) -> None:
        for key, value in (message_attributes or {}).items():
            if "BinaryValue" in value:
                message_attributes[key]["binary_value"] = value.pop("BinaryValue")
            if "StringValue" in value:
                message_attributes[key]["string_value"] = value.pop("StringValue")
            if "DataType" in value:
                message_attributes[key]["data_type"] = value.pop("DataType")

        validate_message_attributes(message_attributes)

    @jsonify_error
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

        self.sqs_backend.get_queue(queue_name)

        if not self.is_json() and self.querystring.get("Entries"):
            raise EmptyBatchRequest()

        if self.is_json():
            entries = {
                str(idx): entry for idx, entry in enumerate(self._get_param("Entries"))
            }
        else:
            entries = {
                str(idx): entry
                for idx, entry in enumerate(
                    self._get_multi_param("SendMessageBatchRequestEntry")
                )
            }

            for entry in entries.values():
                if "MessageAttribute" in entry:
                    entry["MessageAttributes"] = {
                        val["Name"]: val["Value"]
                        for val in entry.pop("MessageAttribute")
                    }

        for entry in entries.values():
            if "MessageAttributes" in entry:
                self.normalize_json_msg_attributes(entry["MessageAttributes"])
            else:
                entry["MessageAttributes"] = {}
            if "DelaySeconds" not in entry:
                entry["DelaySeconds"] = None

        if entries == {}:
            raise EmptyBatchRequest()

        messages = self.sqs_backend.send_message_batch(queue_name, entries)

        if self.is_json():
            resp = {"Successful": [], "Failed": []}
            for msg in messages:
                msg_dict = {
                    "Id": msg.user_id,
                    "MessageId": msg.id,
                    "MD5OfMessageBody": msg.body_md5,
                }
                if len(msg.message_attributes) > 0:
                    msg_dict["MD5OfMessageAttributes"] = msg.attribute_md5
                resp["Successful"].append(msg_dict)
            return json.dumps(resp)

        template = self.response_template(SEND_MESSAGE_BATCH_RESPONSE)
        return template.render(messages=messages)

    @jsonify_error
    def delete_message(self):
        queue_name = self._get_queue_name()
        if self.is_json():
            receipt_handle = self._get_param("ReceiptHandle")
        else:
            receipt_handle = self.querystring.get("ReceiptHandle")[0]
        self.sqs_backend.delete_message(queue_name, receipt_handle)

        if self.is_json():
            return "{}"

        template = self.response_template(DELETE_MESSAGE_RESPONSE)
        return template.render()

    @jsonify_error
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

        if self.is_json():
            receipts = self._get_param("Entries")
        else:
            receipts = self._get_multi_param("DeleteMessageBatchRequestEntry")

        for r in receipts:
            for key in list(r.keys()):
                if key == "Id":
                    r["msg_user_id"] = r.pop(key)
                else:
                    r[camelcase_to_underscores(key)] = r.pop(key)

        receipt_seen = set()
        for receipt_and_id in receipts:
            receipt = receipt_and_id["receipt_handle"]
            if receipt in receipt_seen:
                raise BatchEntryIdsNotDistinct(receipt_and_id["msg_user_id"])
            receipt_seen.add(receipt)

        success = []
        errors = []
        for receipt_and_id in receipts:
            try:
                self.sqs_backend.delete_message(
                    queue_name, receipt_and_id["receipt_handle"]
                )
                success.append(receipt_and_id["msg_user_id"])
            except ReceiptHandleIsInvalid:
                errors.append(
                    {
                        "Id": receipt_and_id["msg_user_id"],
                        "SenderFault": True,
                        "Code": "ReceiptHandleIsInvalid",
                        "Message": f'The input receipt handle "{receipt_and_id["receipt_handle"]}" is not a valid receipt handle.',
                    }
                )

        if self.is_json():
            return json.dumps(
                {"Successful": [{"Id": _id} for _id in success], "Failed": errors}
            )

        template = self.response_template(DELETE_MESSAGE_BATCH_RESPONSE)
        return template.render(success=success, errors=errors)

    @jsonify_error
    def purge_queue(self):
        queue_name = self._get_queue_name()
        self.sqs_backend.purge_queue(queue_name)
        template = self.response_template(PURGE_QUEUE_RESPONSE)
        return template.render()

    @jsonify_error
    def receive_message(self):
        queue_name = self._get_queue_name()
        if self.is_json():
            message_attributes = self._get_param("MessageAttributeNames")
        else:
            message_attributes = self._get_multi_param("message_attributes")
        if not message_attributes:
            message_attributes = extract_input_message_attributes(self.querystring)

        if self.is_json():
            attribute_names = self._get_param("AttributeNames", [])
        else:
            attribute_names = self._get_multi_param("AttributeName")

        queue = self.sqs_backend.get_queue(queue_name)

        try:
            if self.is_json():
                message_count = self._get_param(
                    "MaxNumberOfMessages", DEFAULT_RECEIVED_MESSAGES
                )
            else:
                message_count = int(self.querystring.get("MaxNumberOfMessages")[0])
        except TypeError:
            message_count = DEFAULT_RECEIVED_MESSAGES

        if message_count < 1 or message_count > 10:
            return self._error(
                "InvalidParameterValue",
                "An error occurred (InvalidParameterValue) when calling "
                "the ReceiveMessage operation: Value %s for parameter "
                "MaxNumberOfMessages is invalid. Reason: must be between "
                "1 and 10, if provided." % message_count,
            )

        try:
            if self.is_json():
                wait_time = int(self._get_param("WaitTimeSeconds"))
            else:
                wait_time = int(self.querystring.get("WaitTimeSeconds")[0])
        except TypeError:
            wait_time = int(queue.receive_message_wait_time_seconds)

        if wait_time < 0 or wait_time > 20:
            return self._error(
                "InvalidParameterValue",
                "An error occurred (InvalidParameterValue) when calling "
                "the ReceiveMessage operation: Value %s for parameter "
                "WaitTimeSeconds is invalid. Reason: must be &lt;= 0 and "
                "&gt;= 20 if provided." % wait_time,
            )

        try:
            visibility_timeout = self._get_validated_visibility_timeout()
        except TypeError:
            visibility_timeout = queue.visibility_timeout
        except ValueError:
            return 400, {}, ERROR_MAX_VISIBILITY_TIMEOUT_RESPONSE

        messages = self.sqs_backend.receive_message(
            queue_name, message_count, wait_time, visibility_timeout, message_attributes
        )

        attributes = {
            "approximate_first_receive_timestamp": False,
            "approximate_receive_count": False,
            "message_deduplication_id": False,
            "message_group_id": False,
            "sender_id": False,
            "sent_timestamp": False,
            "sequence_number": False,
        }

        for attribute in attributes:
            pascalcase_name = camelcase_to_pascal(underscores_to_camelcase(attribute))
            if any(x in ["All", pascalcase_name] for x in attribute_names):
                attributes[attribute] = True

        if self.is_json():
            msgs = []
            for message in messages:
                msg = {
                    "MessageId": message.id,
                    "ReceiptHandle": message.receipt_handle,
                    "MD5OfBody": message.body_md5,
                    "Body": message.original_body,
                    "Attributes": {},
                    "MessageAttributes": {},
                }
                if len(message.message_attributes) > 0:
                    msg["MD5OfMessageAttributes"] = message.attribute_md5
                if attributes["sender_id"]:
                    msg["Attributes"]["SenderId"] = message.sender_id
                if attributes["sent_timestamp"]:
                    msg["Attributes"]["SentTimestamp"] = str(message.sent_timestamp)
                if attributes["approximate_receive_count"]:
                    msg["Attributes"]["ApproximateReceiveCount"] = str(
                        message.approximate_receive_count
                    )
                if attributes["approximate_first_receive_timestamp"]:
                    msg["Attributes"]["ApproximateFirstReceiveTimestamp"] = str(
                        message.approximate_first_receive_timestamp
                    )
                if attributes["message_deduplication_id"]:
                    msg["Attributes"][
                        "MessageDeduplicationId"
                    ] = message.deduplication_id
                if attributes["message_group_id"] and message.group_id is not None:
                    msg["Attributes"]["MessageGroupId"] = message.group_id
                if message.system_attributes and message.system_attributes.get(
                    "AWSTraceHeader"
                ):
                    msg["Attributes"]["AWSTraceHeader"] = message.system_attributes[
                        "AWSTraceHeader"
                    ].get("string_value")
                if (
                    attributes["sequence_number"]
                    and message.sequence_number is not None
                ):
                    msg["Attributes"]["SequenceNumber"] = message.sequence_number
                for name, value in message.message_attributes.items():
                    msg["MessageAttributes"][name] = {"DataType": value["data_type"]}
                    if "Binary" in value["data_type"]:
                        msg["MessageAttributes"][name]["BinaryValue"] = value[
                            "binary_value"
                        ]
                    else:
                        msg["MessageAttributes"][name]["StringValue"] = value[
                            "string_value"
                        ]

                if len(msg["Attributes"]) == 0:
                    msg.pop("Attributes")
                if len(msg["MessageAttributes"]) == 0:
                    msg.pop("MessageAttributes")
                msgs.append(msg)
            return json.dumps({"Messages": msgs} if msgs else {})

        template = self.response_template(RECEIVE_MESSAGE_RESPONSE)
        return template.render(messages=messages, attributes=attributes)

    @jsonify_error
    def list_dead_letter_source_queues(self):
        request_url = urlparse(self.uri)
        queue_name = self._get_queue_name()

        queues = self.sqs_backend.list_dead_letter_source_queues(queue_name)

        if self.is_json():
            return json.dumps(
                {"queueUrls": [queue.url(request_url) for queue in queues]}
            )

        template = self.response_template(LIST_DEAD_LETTER_SOURCE_QUEUES_RESPONSE)
        return template.render(queues=queues, request_url=request_url)

    @jsonify_error
    def add_permission(self):
        queue_name = self._get_queue_name()
        actions = (
            self._get_param("Actions")
            if self.is_json()
            else self._get_multi_param("ActionName")
        )
        account_ids = (
            self._get_param("AWSAccountIds")
            if self.is_json()
            else self._get_multi_param("AWSAccountId")
        )
        label = self._get_param("Label")

        self.sqs_backend.add_permission(queue_name, actions, account_ids, label)

        template = self.response_template(ADD_PERMISSION_RESPONSE)
        return template.render()

    @jsonify_error
    def remove_permission(self):
        queue_name = self._get_queue_name()
        label = self._get_param("Label")

        self.sqs_backend.remove_permission(queue_name, label)

        template = self.response_template(REMOVE_PERMISSION_RESPONSE)
        return template.render()

    @jsonify_error
    def tag_queue(self):
        queue_name = self._get_queue_name()
        if self.is_json():
            tags = self._get_param("Tags")
        else:
            tags = self._get_map_prefix("Tag", key_end=".Key", value_end=".Value")

        self.sqs_backend.tag_queue(queue_name, tags)

        if self.is_json():
            return "{}"

        template = self.response_template(TAG_QUEUE_RESPONSE)
        return template.render()

    @jsonify_error
    def untag_queue(self):
        queue_name = self._get_queue_name()
        tag_keys = (
            self._get_param("TagKeys")
            if self.is_json()
            else self._get_multi_param("TagKey")
        )

        self.sqs_backend.untag_queue(queue_name, tag_keys)

        if self.is_json():
            return "{}"

        template = self.response_template(UNTAG_QUEUE_RESPONSE)
        return template.render()

    @jsonify_error
    def list_queue_tags(self):
        queue_name = self._get_queue_name()

        queue = self.sqs_backend.list_queue_tags(queue_name)

        if self.is_json():
            return json.dumps({"Tags": queue.tags})

        template = self.response_template(LIST_QUEUE_TAGS_RESPONSE)
        return template.render(tags=queue.tags)


CREATE_QUEUE_RESPONSE = """<CreateQueueResponse>
    <CreateQueueResult>
        <QueueUrl>{{ queue_url }}</QueueUrl>
    </CreateQueueResult>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</CreateQueueResponse>"""

GET_QUEUE_URL_RESPONSE = """<GetQueueUrlResponse>
    <GetQueueUrlResult>
        <QueueUrl>{{ queue_url }}</QueueUrl>
    </GetQueueUrlResult>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</GetQueueUrlResponse>"""

LIST_QUEUES_RESPONSE = """<ListQueuesResponse>
    <ListQueuesResult>
        {% for queue in queues %}
            <QueueUrl>{{ queue.url(request_url) }}</QueueUrl>
        {% endfor %}
    </ListQueuesResult>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</ListQueuesResponse>"""

DELETE_QUEUE_RESPONSE = """<DeleteQueueResponse>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</DeleteQueueResponse>"""

GET_QUEUE_ATTRIBUTES_RESPONSE = """<GetQueueAttributesResponse>
  <GetQueueAttributesResult>
    {% for key, value in attributes.items() %}
        {% if value is not none %}
            <Attribute>
                <Name>{{ key }}</Name>
                <Value>{{ value }}</Value>
            </Attribute>
        {% endif %}
    {% endfor %}
  </GetQueueAttributesResult>
  <ResponseMetadata>
    <RequestId></RequestId>
  </ResponseMetadata>
</GetQueueAttributesResponse>"""

SET_QUEUE_ATTRIBUTE_RESPONSE = """<SetQueueAttributesResponse>
    <ResponseMetadata>
        <RequestId></RequestId>
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
        <RequestId></RequestId>
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
          {% if attributes.sender_id %}
          <Attribute>
            <Name>SenderId</Name>
            <Value>{{ message.sender_id }}</Value>
          </Attribute>
          {% endif %}
          {% if attributes.sent_timestamp %}
          <Attribute>
            <Name>SentTimestamp</Name>
            <Value>{{ message.sent_timestamp }}</Value>
          </Attribute>
          {% endif %}
          {% if attributes.approximate_receive_count %}
          <Attribute>
            <Name>ApproximateReceiveCount</Name>
            <Value>{{ message.approximate_receive_count }}</Value>
          </Attribute>
          {% endif %}
          {% if attributes.approximate_first_receive_timestamp %}
          <Attribute>
            <Name>ApproximateFirstReceiveTimestamp</Name>
            <Value>{{ message.approximate_first_receive_timestamp }}</Value>
          </Attribute>
          {% endif %}
          {% if attributes.message_deduplication_id and message.deduplication_id is not none %}
          <Attribute>
            <Name>MessageDeduplicationId</Name>
            <Value>{{ message.deduplication_id }}</Value>
          </Attribute>
          {% endif %}
          {% if attributes.message_group_id and message.group_id is not none %}
          <Attribute>
            <Name>MessageGroupId</Name>
            <Value>{{ message.group_id }}</Value>
          </Attribute>
          {% endif %}
          {% if message.system_attributes and message.system_attributes.get('AWSTraceHeader') is not none %}
          <Attribute>
            <Name>AWSTraceHeader</Name>
            <Value>{{ message.system_attributes.get('AWSTraceHeader',{}).get('string_value') }}</Value>
          </Attribute>
          {% endif %}
          {% if attributes.sequence_number and message.sequence_number is not none %}
          <Attribute>
            <Name>SequenceNumber</Name>
            <Value>{{ message.sequence_number }}</Value>
          </Attribute>
          {% endif %}
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
                <StringValue><![CDATA[{{ value.string_value }}]]></StringValue>
                {% endif %}
              </Value>
            </MessageAttribute>
          {% endfor %}
        </Message>
    {% endfor %}
  </ReceiveMessageResult>
  <ResponseMetadata>
    <RequestId></RequestId>
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
    <RequestId></RequestId>
</ResponseMetadata>
</SendMessageBatchResponse>"""

DELETE_MESSAGE_RESPONSE = """<DeleteMessageResponse>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</DeleteMessageResponse>"""

DELETE_MESSAGE_BATCH_RESPONSE = """<DeleteMessageBatchResponse>
    <DeleteMessageBatchResult>
        {% for message_id in success %}
            <DeleteMessageBatchResultEntry>
                <Id>{{ message_id }}</Id>
            </DeleteMessageBatchResultEntry>
        {% endfor %}
        {% for error_dict in errors %}
        <BatchResultErrorEntry>
            <Id>{{ error_dict['Id'] }}</Id>
            <Code>{{ error_dict['Code'] }}</Code>
            <Message>{{ error_dict['Message'] }}</Message>
            <SenderFault>{{ 'true' if error_dict['SenderFault'] else 'false' }}</SenderFault>
        </BatchResultErrorEntry>
        {% endfor %}
    </DeleteMessageBatchResult>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</DeleteMessageBatchResponse>"""

CHANGE_MESSAGE_VISIBILITY_RESPONSE = """<ChangeMessageVisibilityResponse>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</ChangeMessageVisibilityResponse>"""

CHANGE_MESSAGE_VISIBILITY_BATCH_RESPONSE = """<ChangeMessageVisibilityBatchResponse>
    <ChangeMessageVisibilityBatchResult>
        {% for success_id in success %}
        <ChangeMessageVisibilityBatchResultEntry>
            <Id>{{ success_id }}</Id>
        </ChangeMessageVisibilityBatchResultEntry>
        {% endfor %}
        {% for error_dict in errors %}
        <BatchResultErrorEntry>
            <Id>{{ error_dict['Id'] }}</Id>
            <Code>{{ error_dict['Code'] }}</Code>
            <Message>{{ error_dict['Message'] }}</Message>
            <SenderFault>{{ error_dict['SenderFault'] }}</SenderFault>
        </BatchResultErrorEntry>
        {% endfor %}
    </ChangeMessageVisibilityBatchResult>
    <ResponseMetadata>
        <RequestId>{{ request_id }}</RequestId>
    </ResponseMetadata>
</ChangeMessageVisibilityBatchResponse>"""

PURGE_QUEUE_RESPONSE = """<PurgeQueueResponse>
    <ResponseMetadata>
        <RequestId></RequestId>
    </ResponseMetadata>
</PurgeQueueResponse>"""

LIST_DEAD_LETTER_SOURCE_QUEUES_RESPONSE = """<ListDeadLetterSourceQueuesResponse xmlns="http://queue.amazonaws.com/doc/2012-11-05/">
    <ListDeadLetterSourceQueuesResult>
        {% for queue in queues %}
        <QueueUrl>{{ queue.url(request_url) }}</QueueUrl>
        {% endfor %}
    </ListDeadLetterSourceQueuesResult>
    <ResponseMetadata>
        <RequestId>8ffb921f-b85e-53d9-abcf-d8d0057f38fc</RequestId>
    </ResponseMetadata>
</ListDeadLetterSourceQueuesResponse>"""

ADD_PERMISSION_RESPONSE = """<AddPermissionResponse>
    <ResponseMetadata>
        <RequestId>{{ request_id }}</RequestId>
    </ResponseMetadata>
</AddPermissionResponse>"""

REMOVE_PERMISSION_RESPONSE = """<RemovePermissionResponse>
    <ResponseMetadata>
        <RequestId>{{ request_id }}</RequestId>
    </ResponseMetadata>
</RemovePermissionResponse>"""

TAG_QUEUE_RESPONSE = """<TagQueueResponse>
   <ResponseMetadata>
      <RequestId>{{ request_id }}</RequestId>
   </ResponseMetadata>
</TagQueueResponse>"""

UNTAG_QUEUE_RESPONSE = """<UntagQueueResponse>
   <ResponseMetadata>
      <RequestId>{{ request_id }}</RequestId>
   </ResponseMetadata>
</UntagQueueResponse>"""

LIST_QUEUE_TAGS_RESPONSE = """<ListQueueTagsResponse>
   <ListQueueTagsResult>
      {% for key, value in tags.items() %}
      <Tag>
         <Key>{{ key }}</Key>
         <Value>{{ value }}</Value>
      </Tag>
      {% endfor %}
   </ListQueueTagsResult>
   <ResponseMetadata>
      <RequestId>{{ request_id }}</RequestId>
   </ResponseMetadata>
</ListQueueTagsResponse>"""

ERROR_MAX_VISIBILITY_TIMEOUT_RESPONSE = (
    f"Invalid request, maximum visibility timeout is {MAXIMUM_VISIBILTY_TIMEOUT}"
)

ERROR_INEXISTENT_QUEUE = """<ErrorResponse xmlns="http://queue.amazonaws.com/doc/2012-11-05/">
    <Error>
        <Type>Sender</Type>
        <Code>AWS.SimpleQueueService.NonExistentQueue</Code>
         {% if queue_name %}
            <Message>The specified queue {{queue_name}} does not exist for this wsdl version.</Message>
        {% else %}
            <Message>The specified queue does not exist for this wsdl version.</Message>
        {% endif %}
        <Detail/>
    </Error>
    <RequestId>b8bc806b-fa6b-53b5-8be8-cfa2f9836bc3</RequestId>
</ErrorResponse>"""

ERROR_TEMPLATE = """<ErrorResponse xmlns="http://queue.amazonaws.com/doc/2012-11-05/">
    <Error>
        <Type>Sender</Type>
        <Code>{{ code }}</Code>
        <Message>{{ message }}</Message>
        <Detail/>
    </Error>
    <RequestId>6fde8d1e-52cd-4581-8cd9-c512f4c64223</RequestId>
</ErrorResponse>"""
