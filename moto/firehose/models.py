"""FirehoseBackend class with methods for supported APIs."""
import time

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID

from moto.firehose.exceptions import (
    ConcurrentModificationException,
    InvalidArgumentException,
    LimitExceededException,
    ResourceInUseException,
    ResourceNotFoundException,
    ValidationException,
)

from moto.utilities.tagging_service import TaggingService

MAX_TAGS_PER_DELIVERY_STREAM = 50

DESTINATION_TYPES_TO_NAMES = {
    # Implemented
    "s3": "S3",
    "extended_s3": "ExtendedS3",
    "http_endpoint": "HttpEndpoint",
    # Unimplemented
    "elasticsearch": "Elasticsearch",
    "redshift": "Redshift",
    "splunk": "Splunk",
}


def destination_config_in_args(api_args):
    """Return (config_arg, config_name) tuple for destination config.

    The alternative is to use a bunch of 'if' statements to check each
    destination configuration type to see if it's null and then to act
    accordingly.

    It's useful to have names for the types of destination when comparing
    current and replacement destinations.
    """
    destination_names = DESTINATION_TYPES_TO_NAMES.keys()
    configs = []
    for arg_name, arg_value in api_args.items():
        if "_destination" not in arg_name:
            continue

        name = arg_name.split("_destination")[0]
        if name in destination_names and arg_value:
            configs.append((DESTINATION_TYPES_TO_NAMES[name], arg_value))

    # Only a single destination configuration is allowed.
    if len(configs) > 1:
        raise InvalidArgumentException(
            "Exactly one destination configuration is supported for a Firehose"
        )
    return configs[0]


def report_unimplemented_destination(destination_name):
    """Raise exception for unimplemented destinations."""
    if destination_name in ["Redshift", "Elasticsearch", "Splunk"]:
        raise NotImplementedError(
            "A {name} destination delivery stream is not yet implemented"
        )


def create_s3_destination_config(extended_s3_destination_config):
    """Return dict with selected fields copied from ExtendedS3 config.

    This has something to do with S3 being deprecated.
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

        self.delivery_stream_status = "ACTIVE"
        self.delivery_stream_arn = f"arn:aws:firehose:{region}:{ACCOUNT_ID}:/delivery_stream/{delivery_stream_name}"

        self.create_timestamp = time.time()
        self.version_id = "1"  # Used to track updates of destination configs


class FirehoseBackend(BaseBackend):
    """Implementation of Firehose APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.delivery_streams = {}
        self.tagger = TaggingService()

    def lookup_name_from_arn(self, arn):
        """Given an ARN, return the associated delivery stream name."""
        # TODO - need to test
        return self.delivery_streams.get(arn.split("/")[-1])

    def reset(self):
        """Re-initializes all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

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
        (destination_name, destination_config) = destination_config_in_args(locals())

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
            raise NotImplementedError(
                "A delivery stream with server-side encryption enabled is not "
                "yet implemented"
            )

        report_unimplemented_destination(destination_name)

        # Validate the tags before proceeding.
        errmsg = self.tagger.validate_tags(tags or [])
        if errmsg:
            raise ValidationException(errmsg)

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

        # The following logic is not applicable for moto as far as I can tell.
        # if delivery_stream.delivery_stream_status == "CREATING":
        #     raise ResourceInUseException(
        #         f"The hose {delivery_stream_name} is currently being deleted.
        #         f"Please retry after some time"
        #     )
        delivery_stream.delivery_stream_status = "DELETING"
        self.delivery_streams.pop(delivery_stream_name)

    def describe_delivery_stream(
        self, delivery_stream_name, limit, exclusive_start_destination_id,
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

        result = {"DeliveryStreamDescription": {}, "HasMoreDestinations": False}
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
        self, delivery_stream_name, exclusive_start_tag_key, limit,
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

    def tag_delivery_stream(self, delivery_stream_name, tags):
        """Add/update tags for specified delivery stream."""
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under account {ACCOUNT_ID} "
                f"not found."
            )

        if len(tags) >= MAX_TAGS_PER_DELIVERY_STREAM:
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
        (destination_name, destination_config) = destination_config_in_args(locals())

        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(
                f"Firehose {delivery_stream_name} under accountId "
                f"{ACCOUNT_ID} not found."
            )

        report_unimplemented_destination(destination_name)

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
        delivery_stream.last_update_timestamp = time.time()

        # Unimplemented: processing of the "S3BackupMode" parameter.  Per the
        # documentation:  "You can update a delivery stream to enable Amazon
        # S3 backup if it is disabled.  If backup is enabled, you can't update
        # the delivery stream to disable it."


firehose_backends = {}
for available_region in Session().get_available_regions("firehose"):
    firehose_backends[available_region] = FirehoseBackend()
for available_region in Session().get_available_regions(
    "firehose", partition_name="aws-us-gov"
):
    firehose_backends[available_region] = FirehoseBackend()
for available_region in Session().get_available_regions(
    "firehose", partition_name="aws-cn"
):
    firehose_backends[available_region] = FirehoseBackend()
