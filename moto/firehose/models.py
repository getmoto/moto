"""FirehoseBackend class with methods for supported APIs.

Incomplete list of unfinished items:
  - The create_delivery_stream() argument
    DeliveryStreamEncryptionConfigurationInput is not supported.
  - The S3BackupMode argument is ignored as are most of the other
    destination arguments.
  - Data record size and number of transactions are ignored.
  - Better validation of delivery destination parameters, e.g.,
    validation of the url for an http endpoint (boto3 does this).
  - Better handling of the put_record_batch() API.  Not only is
    the existing logic bare bones, but for the ElasticSearch and
    RedShift destinations, the data is just ignored.
  - put_record_batch() handling of errors is minimal and no errors
    are reported back to the user.  Instead an exception is raised.
  - put_record(), put_record_batch() always set "Encrypted" to False.
"""
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from gzip import GzipFile
import io
import json
from time import time
from uuid import uuid4
import warnings

import requests

from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID
from moto.core.utils import BackendDict
from moto.firehose.exceptions import (
    ConcurrentModificationException,
    InvalidArgumentException,
    LimitExceededException,
    ResourceInUseException,
    ResourceNotFoundException,
    ValidationException,
)
from moto.s3 import s3_backend
from moto.utilities.tagging_service import TaggingService

MAX_TAGS_PER_DELIVERY_STREAM = 50

DESTINATION_TYPES_TO_NAMES = {
    "s3": "S3",
    "extended_s3": "ExtendedS3",
    "http_endpoint": "HttpEndpoint",
    "elasticsearch": "Elasticsearch",
    "redshift": "Redshift",
    "splunk": "Splunk",  # Unimplemented
}


def find_destination_config_in_args(api_args):
    """Return (config_arg, config_name) tuple for destination config.

    Determines which destination config(s) have been specified.  The
    alternative is to use a bunch of 'if' statements to check each
    destination configuration.  If more than one destination config is
    specified, than an exception is raised.

    A logical name for the destination type is returned along with the
    destination config as it's useful way to compare current and replacement
    destinations.
    """
    destination_names = DESTINATION_TYPES_TO_NAMES.keys()
    configs = []
    for arg_name, arg_value in api_args.items():
        # Ignore arguments that are not destination configs.
        if "_destination" not in arg_name:
            continue

        # If the destination config value is non-null, save it.
        name = arg_name.split("_destination")[0]
        if name in destination_names and arg_value:
            configs.append((DESTINATION_TYPES_TO_NAMES[name], arg_value))

    # One and only one destination configuration is allowed.
    if len(configs) != 1:
        raise InvalidArgumentException(
            "Exactly one destination configuration is supported for a Firehose"
        )

    return configs[0]


def create_s3_destination_config(extended_s3_destination_config):
    """Return dict with selected fields copied from ExtendedS3 config.

    When an ExtendedS3 config is chosen, AWS tacks on a S3 config as
    well.  When the same field names for S3 and ExtendedS3 exists,
    the ExtendedS3 fields are copied to the added S3 destination.
    """
    fields_not_needed = [
        "S3BackupMode",
        "S3Description",
        "DataFormatconversionConfiguration",
        "DynamicPartitionConfiguration",
    ]
    destination = {}
    for field, value in extended_s3_destination_config.items():
        if field in fields_not_needed:
            continue
        destination[field] = value
    return destination


class DeliveryStream(
    BaseModel
):  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Represents a delivery stream, its source and destination configs."""

    STATES = {"CREATING", "ACTIVE", "CREATING_FAILED"}

    MAX_STREAMS_PER_REGION = 50

    def __init__(
        self,
        region,
        delivery_stream_name,
        delivery_stream_type,
        kinesis_stream_source_configuration,
        destination_name,
        destination_config,
    ):  # pylint: disable=too-many-arguments
        self.delivery_stream_status = "CREATING"
        self.delivery_stream_name = delivery_stream_name
        self.delivery_stream_type = (
            delivery_stream_type if delivery_stream_type else "DirectPut"
        )

        self.source = kinesis_stream_source_configuration
        self.destinations = [
            {
                "destination_id": "destinationId-000000000001",
                destination_name: destination_config,
            }
        ]
        if destination_name == "ExtendedS3":
            # Add a S3 destination as well, minus a few ExtendedS3 fields.
            self.destinations[0]["S3"] = create_s3_destination_config(
                destination_config
            )
        elif "S3Configuration" in destination_config:
            # S3Configuration becomes S3DestinationDescription for the
            # other destinations.
            self.destinations[0][destination_name][
                "S3DestinationDescription"
            ] = destination_config["S3Configuration"]
            del self.destinations[0][destination_name]["S3Configuration"]

        self.delivery_stream_status = "ACTIVE"
        self.delivery_stream_arn = f"arn:aws:firehose:{region}:{ACCOUNT_ID}:deliverystream/{delivery_stream_name}"

        self.create_timestamp = datetime.now(timezone.utc).isoformat()
        self.version_id = "1"  # Used to track updates of destination configs

        # I believe boto3 only adds this field after an update ...
        self.last_update_timestamp = datetime.now(timezone.utc).isoformat()


class FirehoseBackend(BaseBackend):
    """Implementation of Firehose APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.delivery_streams = {}
        self.tagger = TaggingService()

    def reset(self):
        """Re-initializes all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "firehose", special_service_name="kinesis-firehose"
        )

    def create_delivery_stream(
        self,
        region,
        delivery_stream_name,
        delivery_stream_type,
        kinesis_stream_source_configuration,
        delivery_stream_encryption_configuration_input,
        s3_destination_configuration,
        extended_s3_destination_configuration,
        redshift_destination_configuration,
        elasticsearch_destination_configuration,
        splunk_destination_configuration,
        http_endpoint_destination_configuration,
        tags,
    ):  # pylint: disable=too-many-arguments,too-many-locals,unused-argument
        """Create a Kinesis Data Firehose delivery stream."""
        (destination_name, destination_config) = find_destination_config_in_args(
            locals()
        )

        if delivery_stream_name in self.delivery_streams:
            raise ResourceInUseException(
                f"Firehose {delivery_stream_name} under accountId {ACCOUNT_ID} "
                f"already exists"
            )

        if len(self.delivery_streams) == DeliveryStream.MAX_STREAMS_PER_REGION:
            raise LimitExceededException(
                f"You have already consumed your firehose quota of "
                f"{DeliveryStream.MAX_STREAMS_PER_REGION} hoses. Firehose "
                f"names: {list(self.delivery_streams.keys())}"
            )

        # Rule out situations that are not yet implemented.
        if delivery_stream_encryption_configuration_input:
            warnings.warn(
                "A delivery stream with server-side encryption enabled is not "
                "yet implemented"
            )

        if destination_name == "Splunk":
            warnings.warn("A Splunk destination delivery stream is not yet implemented")

        if (
            kinesis_stream_source_configuration
            and delivery_stream_type != "KinesisStreamAsSource"
        ):
            raise InvalidArgumentException(
                "KinesisSourceStreamConfig is only applicable for "
                "KinesisStreamAsSource stream type"
            )

        # Validate the tags before proceeding.
        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise ValidationException(errmsg)

        if tags and len(tags) > MAX_TAGS_PER_DELIVERY_STREAM:
            raise ValidationException(
                f"1 validation error detected: Value '{tags}' at 'tags' "
                f"failed to satisify contstraint: Member must have length "
                f"less than or equal to {MAX_TAGS_PER_DELIVERY_STREAM}"
            )

        # Create a DeliveryStream instance that will be stored and indexed
        # by delivery stream name.  This instance will update the state and
        # create the ARN.
        delivery_stream = DeliveryStream(
            region,
            delivery_stream_name,
            delivery_stream_type,
            kinesis_stream_source_configuration,
            destination_name,
            destination_config,
        )
        self.tagger.tag_resource(delivery_stream.delivery_stream_arn, tags or [])

        self.delivery_streams[delivery_stream_name] = delivery_stream
        return self.delivery_streams[delivery_stream_name].delivery_stream_arn

    def delete_delivery_stream(
        self, delivery_stream_name, allow_force_delete=False
    ):  # pylint: disable=unused-argument
        """Delete a delivery stream and its data.

        AllowForceDelete option is ignored as we only superficially
        apply state.
        """
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        self.tagger.delete_all_tags_for_resource(delivery_stream.delivery_stream_arn)

        delivery_stream.delivery_stream_status = "DELETING"
        self.delivery_streams.pop(delivery_stream_name)

    def describe_delivery_stream(
        self, delivery_stream_name, limit, exclusive_start_destination_id
    ):  # pylint: disable=unused-argument
        """Return description of specified delivery stream and its status.

        Note:  the 'limit' and 'exclusive_start_destination_id' parameters
        are not currently processed/implemented.
        """
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        result = {"DeliveryStreamDescription": {"HasMoreDestinations": False}}
        for attribute, attribute_value in vars(delivery_stream).items():
            if not attribute_value:
                continue

            # Convert from attribute's snake case to camel case for outgoing
            # JSON.
            name = "".join([x.capitalize() for x in attribute.split("_")])

            # Fooey ... always an exception to the rule:
            if name == "DeliveryStreamArn":
                name = "DeliveryStreamARN"

            if name != "Destinations":
                if name == "Source":
                    result["DeliveryStreamDescription"][name] = {
                        "KinesisStreamSourceDescription": attribute_value
                    }
                else:
                    result["DeliveryStreamDescription"][name] = attribute_value
                continue

            result["DeliveryStreamDescription"]["Destinations"] = []
            for destination in attribute_value:
                description = {}
                for key, value in destination.items():
                    if key == "destination_id":
                        description["DestinationId"] = value
                    else:
                        description[f"{key}DestinationDescription"] = value

                result["DeliveryStreamDescription"]["Destinations"].append(description)

        return result

    def list_delivery_streams(
        self, limit, delivery_stream_type, exclusive_start_delivery_stream_name
    ):
        """Return list of delivery streams in alphabetic order of names."""
        result = {"DeliveryStreamNames": [], "HasMoreDeliveryStreams": False}
        if not self.delivery_streams:
            return result

        # If delivery_stream_type is specified, filter out any stream that's
        # not of that type.
        stream_list = self.delivery_streams.keys()
        if delivery_stream_type:
            stream_list = [
                x
                for x in stream_list
                if self.delivery_streams[x].delivery_stream_type == delivery_stream_type
            ]

        # The list is sorted alphabetically, not alphanumerically.
        sorted_list = sorted(stream_list)

        # Determine the limit or number of names to return in the list.
        limit = limit or DeliveryStream.MAX_STREAMS_PER_REGION

        # If a starting delivery stream name is given, find the index into
        # the sorted list, then add one to get the name following it.  If the
        # exclusive_start_delivery_stream_name doesn't exist, it's ignored.
        start = 0
        if exclusive_start_delivery_stream_name:
            if self.delivery_streams.get(exclusive_start_delivery_stream_name):
                start = sorted_list.index(exclusive_start_delivery_stream_name) + 1

        result["DeliveryStreamNames"] = sorted_list[start : start + limit]
        if len(sorted_list) > (start + limit):
            result["HasMoreDeliveryStreams"] = True
        return result

    def list_tags_for_delivery_stream(
        self, delivery_stream_name, exclusive_start_tag_key, limit
    ):
        """Return list of tags."""
        result = {"Tags": [], "HasMoreTags": False}
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        tags = self.tagger.list_tags_for_resource(delivery_stream.delivery_stream_arn)[
            "Tags"
        ]
        keys = self.tagger.extract_tag_names(tags)

        # If a starting tag is given and can be found, find the index into
        # tags, then add one to get the tag following it.
        start = 0
        if exclusive_start_tag_key:
            if exclusive_start_tag_key in keys:
                start = keys.index(exclusive_start_tag_key) + 1

        limit = limit or MAX_TAGS_PER_DELIVERY_STREAM
        result["Tags"] = tags[start : start + limit]
        if len(tags) > (start + limit):
            result["HasMoreTags"] = True
        return result

    def put_record(self, delivery_stream_name, record):
        """Write a single data record into a Kinesis Data firehose stream."""
        result = self.put_record_batch(delivery_stream_name, [record])
        return {
            "RecordId": result["RequestResponses"][0]["RecordId"],
            "Encrypted": False,
        }

    @staticmethod
    def put_http_records(http_destination, records):
        """Put records to a HTTP destination."""
        # Mostly copied from localstack
        url = http_destination["EndpointConfiguration"]["Url"]
        headers = {"Content-Type": "application/json"}
        record_to_send = {
            "requestId": str(uuid4()),
            "timestamp": int(time()),
            "records": [{"data": record["Data"]} for record in records],
        }
        try:
            requests.post(url, json=record_to_send, headers=headers)
        except Exception as exc:
            # This could be better ...
            raise RuntimeError(
                "Firehose PutRecord(Batch) to HTTP destination failed"
            ) from exc
        return [{"RecordId": str(uuid4())} for _ in range(len(records))]

    @staticmethod
    def _format_s3_object_path(delivery_stream_name, version_id, prefix):
        """Return a S3 object path in the expected format."""
        # Taken from LocalStack's firehose logic, with minor changes.
        # See https://docs.aws.amazon.com/firehose/latest/dev/basic-deliver.html#s3-object-name
        # Path prefix pattern: myApp/YYYY/MM/DD/HH/
        # Object name pattern:
        # DeliveryStreamName-DeliveryStreamVersion-YYYY-MM-DD-HH-MM-SS-RandomString
        prefix = f"{prefix}{'' if prefix.endswith('/') else '/'}"
        now = datetime.utcnow()
        return (
            f"{prefix}{now.strftime('%Y/%m/%d/%H')}/"
            f"{delivery_stream_name}-{version_id}-"
            f"{now.strftime('%Y-%m-%d-%H-%M-%S')}-{str(uuid4())}"
        )

    def put_s3_records(self, delivery_stream_name, version_id, s3_destination, records):
        """Put records to a ExtendedS3 or S3 destination."""
        # Taken from LocalStack's firehose logic, with minor changes.
        bucket_name = s3_destination["BucketARN"].split(":")[-1]
        prefix = s3_destination.get("Prefix", "")
        object_path = self._format_s3_object_path(
            delivery_stream_name, version_id, prefix
        )

        batched_data = b"".join([b64decode(r["Data"]) for r in records])
        try:
            s3_backend.put_object(bucket_name, object_path, batched_data)
        except Exception as exc:
            # This could be better ...
            raise RuntimeError(
                "Firehose PutRecord(Batch to S3 destination failed"
            ) from exc
        return [{"RecordId": str(uuid4())} for _ in range(len(records))]

    def put_record_batch(self, delivery_stream_name, records):
        """Write multiple data records into a Kinesis Data firehose stream."""
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        request_responses = []
        for destination in delivery_stream.destinations:
            if "ExtendedS3" in destination:
                # ExtendedS3 will be handled like S3,but in the future
                # this will probably need to be revisited.  This destination
                # must be listed before S3 otherwise both destinations will
                # be processed instead of just ExtendedS3.
                request_responses = self.put_s3_records(
                    delivery_stream_name,
                    delivery_stream.version_id,
                    destination["ExtendedS3"],
                    records,
                )
            elif "S3" in destination:
                request_responses = self.put_s3_records(
                    delivery_stream_name,
                    delivery_stream.version_id,
                    destination["S3"],
                    records,
                )
            elif "HttpEndpoint" in destination:
                request_responses = self.put_http_records(
                    destination["HttpEndpoint"], records
                )
            elif "Elasticsearch" in destination or "Redshift" in destination:
                # This isn't implmented as these services aren't implemented,
                # so ignore the data, but return a "proper" response.
                request_responses = [
                    {"RecordId": str(uuid4())} for _ in range(len(records))
                ]

        return {
            "FailedPutCount": 0,
            "Encrypted": False,
            "RequestResponses": request_responses,
        }

    def tag_delivery_stream(self, delivery_stream_name, tags):
        """Add/update tags for specified delivery stream."""
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        if len(tags) > MAX_TAGS_PER_DELIVERY_STREAM:
            raise ValidationException(
                f"1 validation error detected: Value '{tags}' at 'tags' "
                f"failed to satisify contstraint: Member must have length "
                f"less than or equal to {MAX_TAGS_PER_DELIVERY_STREAM}"
            )

        errmsg = self.tagger.validate_tags(tags)
        if errmsg:
            raise ValidationException(errmsg)

        self.tagger.tag_resource(delivery_stream.delivery_stream_arn, tags)

    def untag_delivery_stream(self, delivery_stream_name, tag_keys):
        """Removes tags from specified delivery stream."""
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        # If a tag key doesn't exist for the stream, boto3 ignores it.
        self.tagger.untag_resource_using_names(
            delivery_stream.delivery_stream_arn, tag_keys
        )

    def update_destination(
        self,
        delivery_stream_name,
        current_delivery_stream_version_id,
        destination_id,
        s3_destination_update,
        extended_s3_destination_update,
        s3_backup_mode,
        redshift_destination_update,
        elasticsearch_destination_update,
        splunk_destination_update,
        http_endpoint_destination_update,
    ):  # pylint: disable=unused-argument,too-many-arguments,too-many-locals
        """Updates specified destination of specified delivery stream."""
        (destination_name, destination_config) = find_destination_config_in_args(
            locals()
        )

        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under accountId "
                f"{ACCOUNT_ID} not found."
            )

        if destination_name == "Splunk":
            warnings.warn("A Splunk destination delivery stream is not yet implemented")

        if delivery_stream.version_id != current_delivery_stream_version_id:
            raise ConcurrentModificationException(
                f"Cannot update firehose: {delivery_stream_name} since the "
                f"current version id: {delivery_stream.version_id} and "
                f"specified version id: {current_delivery_stream_version_id} "
                f"do not match"
            )

        destination = {}
        destination_idx = 0
        for destination in delivery_stream.destinations:
            if destination["destination_id"] == destination_id:
                break
            destination_idx += 1
        else:
            raise InvalidArgumentException("Destination Id {destination_id} not found")

        # Switching between Amazon ES and other services is not supported.
        # For an Amazon ES destination, you can only update to another Amazon
        # ES destination.  Same with HTTP.  Didn't test Splunk.
        if (
            destination_name == "Elasticsearch" and "Elasticsearch" not in destination
        ) or (destination_name == "HttpEndpoint" and "HttpEndpoint" not in destination):
            raise InvalidArgumentException(
                f"Changing the destination type to or from {destination_name} "
                f"is not supported at this time."
            )

        # If this is a different type of destination configuration,
        # the existing configuration is reset first.
        if destination_name in destination:
            delivery_stream.destinations[destination_idx][destination_name].update(
                destination_config
            )
        else:
            delivery_stream.destinations[destination_idx] = {
                "destination_id": destination_id,
                destination_name: destination_config,
            }

        # Once S3 is updated to an ExtendedS3 destination, both remain in
        # the destination.  That means when one is updated, the other needs
        # to be updated as well.  The problem is that they don't have the
        # same fields.
        if destination_name == "ExtendedS3":
            delivery_stream.destinations[destination_idx][
                "S3"
            ] = create_s3_destination_config(destination_config)
        elif destination_name == "S3" and "ExtendedS3" in destination:
            destination["ExtendedS3"] = {
                k: v
                for k, v in destination["S3"].items()
                if k in destination["ExtendedS3"]
            }

        # Increment version number and update the timestamp.
        delivery_stream.version_id = str(int(current_delivery_stream_version_id) + 1)
        delivery_stream.last_update_timestamp = datetime.now(timezone.utc).isoformat()

        # Unimplemented: processing of the "S3BackupMode" parameter.  Per the
        # documentation:  "You can update a delivery stream to enable Amazon
        # S3 backup if it is disabled.  If backup is enabled, you can't update
        # the delivery stream to disable it."

    def lookup_name_from_arn(self, arn):
        """Given an ARN, return the associated delivery stream name."""
        return self.delivery_streams.get(arn.split("/")[-1])

    def send_log_event(
        self,
        delivery_stream_arn,
        filter_name,
        log_group_name,
        log_stream_name,
        log_events,
    ):  # pylint:  disable=too-many-arguments
        """Send log events to a S3 bucket after encoding and gzipping it."""
        data = {
            "logEvents": log_events,
            "logGroup": log_group_name,
            "logStream": log_stream_name,
            "messageType": "DATA_MESSAGE",
            "owner": ACCOUNT_ID,
            "subscriptionFilters": [filter_name],
        }

        output = io.BytesIO()
        with GzipFile(fileobj=output, mode="w") as fhandle:
            fhandle.write(json.dumps(data, separators=(",", ":")).encode("utf-8"))
        gzipped_payload = b64encode(output.getvalue()).decode("utf-8")

        delivery_stream = self.lookup_name_from_arn(delivery_stream_arn)
        self.put_s3_records(
            delivery_stream.delivery_stream_name,
            delivery_stream.version_id,
            delivery_stream.destinations[0]["S3"],
            [{"Data": gzipped_payload}],
        )


firehose_backends = BackendDict(FirehoseBackend, "firehose")
