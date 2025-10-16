import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from moto.core.responses import ActionResult, BaseResponse, EmptyResult
from moto.core.utils import (
    camelcase_to_pascal,
    camelcase_to_underscores,
    underscores_to_camelcase,
)
from moto.utilities.aws_headers import amz_crc32

from ..core.common_types import TYPE_RESPONSE
from .constants import (
    DEFAULT_RECEIVED_MESSAGES,
    MAXIMUM_MESSAGE_LENGTH,
    MAXIMUM_VISIBILITY_TIMEOUT,
)
from .exceptions import (
    BatchEntryIdsNotDistinct,
    EmptyBatchRequest,
    InvalidAttributeName,
    MaxVisibilityTimeout,
    SQSException,
)
from .models import SQSBackend, sqs_backends
from .utils import validate_message_attributes


class SQSResponse(BaseResponse):
    region_regex = re.compile(r"://(.+?)\.queue\.amazonaws\.com")

    def __init__(self) -> None:
        super().__init__(service_name="sqs")
        self.automated_parameter_parsing = True

    @property
    def sqs_backend(self) -> SQSBackend:
        return sqs_backends[self.current_account][self.region]

    def _get_queue_name(self) -> str:
        try:
            queue_url = self._get_param("QueueUrl")
            if queue_url.startswith("http://") or queue_url.startswith("https://"):
                return queue_url.split("/")[-1]
            else:
                # The parameter could be the name itself, which AWS also accepts
                return queue_url
        except (AttributeError, TypeError):
            pass
        # Fallback to reading from the URL for botocore
        return self.path.split("/")[-1]

    def _get_validated_visibility_timeout(self, timeout: Optional[str] = None) -> int:
        """
        :raises ValueError: If specified visibility timeout exceeds MAXIMUM_VISIBILITY_TIMEOUT
        :raises TypeError: If visibility timeout was not specified
        """
        if timeout is not None:
            visibility_timeout = int(timeout)
        else:
            visibility_timeout = self._get_param("VisibilityTimeout")
        if visibility_timeout > MAXIMUM_VISIBILITY_TIMEOUT:
            raise ValueError
        return visibility_timeout

    @amz_crc32  # crc last as request_id can edit XML
    def call_action(self) -> TYPE_RESPONSE:
        return super().call_action()

    def create_queue(self) -> ActionResult:
        request_url = urlparse(self.uri)
        queue_name = self._get_param("QueueName")
        attributes = self._get_param("Attributes", {})
        tags = self._get_param("tags", {})
        queue = self.sqs_backend.create_queue(queue_name, tags, **attributes)
        result = {"QueueUrl": queue.url(request_url)}
        return ActionResult(result)

    def get_queue_url(self) -> ActionResult:
        request_url = urlparse(self.uri)
        queue_name = self._get_param("QueueName")
        queue = self.sqs_backend.get_queue_url(queue_name)
        result = {"QueueUrl": queue.url(request_url)}
        return ActionResult(result)

    def list_queues(self) -> ActionResult:
        request_url = urlparse(self.uri)
        queue_name_prefix = self._get_param("QueueNamePrefix")
        queues = self.sqs_backend.list_queues(queue_name_prefix)
        result = {}
        if queues:
            result["QueueUrls"] = [queue.url(request_url) for queue in queues]
        return ActionResult(result)

    def change_message_visibility(self) -> ActionResult:
        queue_name = self._get_queue_name()
        receipt_handle = self._get_param("ReceiptHandle")
        try:
            visibility_timeout = self._get_validated_visibility_timeout()
        except ValueError:
            raise MaxVisibilityTimeout()
        self.sqs_backend.change_message_visibility(
            queue_name=queue_name,
            receipt_handle=receipt_handle,
            visibility_timeout=visibility_timeout,
        )
        return EmptyResult()

    def change_message_visibility_batch(self) -> ActionResult:
        queue_name = self._get_queue_name()
        entries = self._get_param("Entries", [])
        success, failed = self.sqs_backend.change_message_visibility_batch(
            queue_name, entries
        )
        result = {"Successful": [{"Id": _id} for _id in success], "Failed": failed}
        return ActionResult(result)

    def get_queue_attributes(self) -> ActionResult:
        queue_name = self._get_queue_name()
        attribute_names = self._get_param("AttributeNames", [])
        if attribute_names and "" in attribute_names:
            raise InvalidAttributeName("")
        attributes = self.sqs_backend.get_queue_attributes(queue_name, attribute_names)
        result = {
            "Attributes": {
                key: str(value)
                for key, value in attributes.items()
                if value is not None
            }
        }
        if not result["Attributes"]:
            return EmptyResult()
        return ActionResult(result)

    def set_queue_attributes(self) -> ActionResult:
        # TODO validate self.get_param('QueueUrl')
        attributes = self._get_param("Attributes", {})
        queue_name = self._get_queue_name()
        self.sqs_backend.set_queue_attributes(queue_name, attributes)
        return EmptyResult()

    def delete_queue(self) -> ActionResult:
        # TODO validate self.get_param('QueueUrl')
        queue_name = self._get_queue_name()
        self.sqs_backend.delete_queue(queue_name)
        return EmptyResult()

    def send_message(self) -> ActionResult:
        message = self._get_param("MessageBody")
        delay_seconds = self._get_param("DelaySeconds")
        message_group_id = self._get_param("MessageGroupId")
        message_dedupe_id = self._get_param("MessageDeduplicationId")
        if len(message) > MAXIMUM_MESSAGE_LENGTH:
            raise SQSException(
                "InvalidParameterValue",
                "One or more parameters are invalid. Reason: Message must be shorter than 262144 bytes.",
            )
        message_attributes = self._get_param("MessageAttributes", {})
        self.normalize_json_msg_attributes(message_attributes)
        system_message_attributes = self._get_param("MessageSystemAttributes")
        self.normalize_json_msg_attributes(system_message_attributes)
        queue_name = self._get_queue_name()
        message = self.sqs_backend.send_message(
            queue_name,
            message,
            message_attributes=message_attributes,
            delay_seconds=delay_seconds,
            deduplication_id=message_dedupe_id,
            group_id=message_group_id,
            system_attributes=system_message_attributes,
        )
        resp = {
            "MD5OfMessageBody": message.body_md5,
            "MessageId": message.id,
        }
        if len(message.message_attributes) > 0:
            resp["MD5OfMessageAttributes"] = message.attribute_md5
        return ActionResult(resp)

    def normalize_json_msg_attributes(self, message_attributes: Dict[str, Any]) -> None:
        # TODO: I don't think we need this, right... Just use the PascalCase keys directly.
        for key, value in (message_attributes or {}).items():
            if "BinaryValue" in value:
                message_attributes[key]["binary_value"] = value.pop("BinaryValue")
            if "StringValue" in value:
                message_attributes[key]["string_value"] = value.pop("StringValue")
            if "DataType" in value:
                message_attributes[key]["data_type"] = value.pop("DataType")

        validate_message_attributes(message_attributes)

    def send_message_batch(self) -> ActionResult:
        queue_name = self._get_queue_name()
        self.sqs_backend.get_queue(queue_name)
        entries = self._get_param("Entries", [])
        if not entries:
            raise EmptyBatchRequest()
        entries = {str(idx): entry for idx, entry in enumerate(entries)}
        # This was originally in query parsing - do we still need this?
        # I don't think so.  This was just because of the different parsing
        # between the XML and JSON protocols. (the multi_param stuff maybe didn't pluralize?)
        # for entry in entries.values():
        #     if "MessageAttribute" in entry:
        #         entry["MessageAttributes"] = {
        #             val["Name"]: val["Value"] for val in entry.pop("MessageAttribute")
        #         }

        for entry in entries.values():
            if "MessageAttributes" in entry:
                self.normalize_json_msg_attributes(entry["MessageAttributes"])
            else:
                entry["MessageAttributes"] = {}
            if "DelaySeconds" not in entry:
                entry["DelaySeconds"] = None

        if entries == {}:
            raise EmptyBatchRequest()

        messages, failedInvalidDelay = self.sqs_backend.send_message_batch(
            queue_name, entries
        )

        errors = []
        for entry in failedInvalidDelay:
            errors.append(
                {
                    "Id": entry["Id"],
                    "SenderFault": "true",
                    "Code": "InvalidParameterValue",
                    "Message": "Value 1800 for parameter DelaySeconds is invalid. Reason: DelaySeconds must be &gt;= 0 and &lt;= 900.",
                }
            )

        resp: Dict[str, Any] = {"Successful": [], "Failed": errors}
        for msg in messages:
            msg_dict = {
                "Id": msg.user_id,  # type: ignore
                "MessageId": msg.id,
                "MD5OfMessageBody": msg.body_md5,
            }
            if len(msg.message_attributes) > 0:
                msg_dict["MD5OfMessageAttributes"] = msg.attribute_md5
            resp["Successful"].append(msg_dict)
        return ActionResult(resp)

    def delete_message(self) -> ActionResult:
        queue_name = self._get_queue_name()
        receipt_handle = self._get_param("ReceiptHandle")
        self.sqs_backend.delete_message(queue_name, receipt_handle)
        return EmptyResult()

    def delete_message_batch(self) -> ActionResult:
        queue_name = self._get_queue_name()
        receipts = self._get_param("Entries", [])
        if not receipts:
            raise EmptyBatchRequest(action="Delete")
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
        success, errors = self.sqs_backend.delete_message_batch(queue_name, receipts)
        result = {"Successful": [{"Id": _id} for _id in success], "Failed": errors}
        return ActionResult(result)

    def purge_queue(self) -> ActionResult:
        queue_name = self._get_queue_name()
        self.sqs_backend.purge_queue(queue_name)
        return EmptyResult()

    def receive_message(self) -> ActionResult:
        queue_name = self._get_queue_name()
        message_attributes = self._get_param("MessageAttributeNames", [])
        message_system_attributes = self._get_param("MessageSystemAttributeNames", {})
        attribute_names = self._get_param("AttributeNames", [])
        queue = self.sqs_backend.get_queue(queue_name)
        message_count = self._get_param(
            "MaxNumberOfMessages", DEFAULT_RECEIVED_MESSAGES
        )
        if message_count < 1 or message_count > 10:
            raise SQSException(
                "InvalidParameterValue",
                "An error occurred (InvalidParameterValue) when calling "
                f"the ReceiveMessage operation: Value {message_count} for parameter "
                "MaxNumberOfMessages is invalid. Reason: must be between "
                "1 and 10, if provided.",
            )
        try:
            wait_time = int(self._get_param("WaitTimeSeconds"))
        except TypeError:
            wait_time = int(queue.receive_message_wait_time_seconds)  # type: ignore
        if wait_time < 0 or wait_time > 20:
            raise SQSException(
                "InvalidParameterValue",
                "An error occurred (InvalidParameterValue) when calling "
                f"the ReceiveMessage operation: Value {wait_time} for parameter "
                "WaitTimeSeconds is invalid. Reason: must be &lt;= 0 and "
                "&gt;= 20 if provided.",
            )
        try:
            visibility_timeout = self._get_validated_visibility_timeout()
        except TypeError:
            visibility_timeout = queue.visibility_timeout  # type: ignore
        except ValueError:
            raise MaxVisibilityTimeout()

        messages = self.sqs_backend.receive_message(
            queue_name, message_count, wait_time, visibility_timeout, message_attributes
        )
        # TODO: None of this casing stuff should be necessary...
        attributes = {
            "approximate_first_receive_timestamp": "ApproximateFirstReceiveTimestamp"
            in message_system_attributes,
            "approximate_receive_count": "ApproximateReceiveCount"
            in message_system_attributes,
            "message_deduplication_id": "MessageDeduplicationId"
            in message_system_attributes,
            "message_group_id": "MessageGroupId" in message_system_attributes,
            "sender_id": "SenderId" in message_system_attributes,
            "sent_timestamp": "SentTimestamp" in message_system_attributes,
            "sequence_number": "SequenceNumber" in message_system_attributes,
        }

        if "All" in message_system_attributes:
            attributes = {
                "approximate_first_receive_timestamp": True,
                "approximate_receive_count": True,
                "message_deduplication_id": True,
                "message_group_id": True,
                "sender_id": True,
                "sent_timestamp": True,
                "sequence_number": True,
            }
        # TODO: This is an abomination.  We should just use the PascalCase keys directly.
        for attribute in attributes:
            pascalcase_name = camelcase_to_pascal(underscores_to_camelcase(attribute))
            if any(x in ["All", pascalcase_name] for x in attribute_names):
                attributes[attribute] = True

        msgs = []
        for message in messages:
            msg: Dict[str, Any] = {
                "MessageId": message.id,
                "ReceiptHandle": message.receipt_handle,
                "MD5OfBody": message.body_md5,
                "Body": message.body,
                "Attributes": {},
                "MessageAttributes": {},
            }
            # TODO: If we have the right casing, this just becomes a for loop, right?
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
                msg["Attributes"]["MessageDeduplicationId"] = message.deduplication_id
            if attributes["message_group_id"] and message.group_id is not None:
                msg["Attributes"]["MessageGroupId"] = message.group_id
            if message.system_attributes and message.system_attributes.get(
                "AWSTraceHeader"
            ):
                msg["Attributes"]["AWSTraceHeader"] = message.system_attributes[
                    "AWSTraceHeader"
                ].get("string_value")
            if attributes["sequence_number"] and message.sequence_number is not None:
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

            # Double check this against real AWS. Do they return [] or omit the keys entirely?
            if len(msg["Attributes"]) == 0:
                msg.pop("Attributes")
            if len(msg["MessageAttributes"]) == 0:
                msg.pop("MessageAttributes")
            msgs.append(msg)

        result = {"Messages": msgs} if msgs else {}
        return ActionResult(result)

    def list_dead_letter_source_queues(self) -> ActionResult:
        request_url = urlparse(self.uri)
        queue_name = self._get_queue_name()
        queues = self.sqs_backend.list_dead_letter_source_queues(queue_name)
        result = {"queueUrls": [queue.url(request_url) for queue in queues]}
        return ActionResult(result)

    def add_permission(self) -> ActionResult:
        queue_name = self._get_queue_name()
        actions = self._get_param("Actions", [])
        account_ids = self._get_param("AWSAccountIds", [])
        label = self._get_param("Label")
        self.sqs_backend.add_permission(
            region_name=self.region,
            queue_name=queue_name,
            actions=actions,
            account_ids=account_ids,
            label=label,
        )
        return EmptyResult()

    def remove_permission(self) -> ActionResult:
        queue_name = self._get_queue_name()
        label = self._get_param("Label")
        self.sqs_backend.remove_permission(queue_name, label)
        return EmptyResult()

    def tag_queue(self) -> ActionResult:
        queue_name = self._get_queue_name()
        tags = self._get_param("Tags", [])
        self.sqs_backend.tag_queue(queue_name, tags)
        return EmptyResult()

    def untag_queue(self) -> ActionResult:
        queue_name = self._get_queue_name()
        tag_keys = self._get_param("TagKeys", [])
        self.sqs_backend.untag_queue(queue_name, tag_keys)
        return EmptyResult()

    def list_queue_tags(self) -> ActionResult:
        queue_name = self._get_queue_name()
        queue = self.sqs_backend.list_queue_tags(queue_name)
        result = {"Tags": queue.tags}
        return ActionResult(result)
