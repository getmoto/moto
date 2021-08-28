"""FirehoseBackend class with methods for supported APIs."""
from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID

from moto.firehose.exceptions import (
    InvalidArgumentException,
    LimitExceededException,
    ResourceInUseException,
    ResourceNotFoundException,
    InvalidKMSResourceException,
)


class DeliveryStream(BaseModel):  # pylint: disable=too-few-public-methods

    """Represents a delivery stream, its source and destination configs."""

    STATES = {"CREATING", "ACTIVE", "CREATING_FAILED"}
    # TODO - still need?
    DESTINATION_TYPES = {
        "S3",
        "Extended_S3",
        "ElasticSearch",
        "Redshift",
        "Splunk",
        "Http",
    }

    MAX_STREAMS_PER_REGION = 50

    def __init__(
        self,
        region,
        delivery_stream_name,
        delivery_stream_type,
        kinesis_stream_source_configuration,
        destination_type,
        destination_config,
        tags,
    ):  # pylint: disable=too-many-arguments
        # kinesis_stream_source_configuration,
        # s3_destination_configuration,
        # extended_s3_destination_configuration,
        # http_endpoint_destination_configuration,

        # DeliveryStreams: Check validity of bucket_arn.
        self.state = "CREATING"
        self.delivery_stream_name = delivery_stream_name
        self.delivery_stream_type = (
            delivery_stream_type if delivery_stream_type else "DirectPut"
        )

        # Short string representing type, e.g., "Extended_S3", "Http".
        self.destination_type = destination_type
        self.destination_config = destination_config
        self.state = "ACTIVE"
        self.delivery_stream_arn = f"arn:aws:firehose:{region}:{ACCOUNT_ID}:/delivery_stream/{delivery_stream_name}"


class FirehoseBackend(BaseBackend):

    """Implementation of Firehose APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.delivery_streams = {}

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
    ):  # pylint: disable=too-many-arguments,too-many-locals
        """Create a Kinesis Data Firehose delivery stream."""
        # Rule out situations that are not yet implemented.
        if delivery_stream_encryption_configuration_input:
            raise NotImplementedError(
                "A delivery stream with server-side encryption enabled is not "
                "yet implemented"
            )
        if redshift_destination_configuration:
            raise NotImplementedError(
                "A RedShift destination delivery stream is not yet implemented"
            )
        if elasticsearch_destination_configuration:
            raise NotImplementedError(
                "An ElasticSearch destination delivery stream is not yet implemented"
            )
        if splunk_destination_configuration:
            raise NotImplementedError(
                "A Splunk destination delivery stream is not yet implemented"
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

        # At the moment only some of these configurations are supported, but
        # this test for only a single destination configuration will work
        # without change when the other configurations are implemented.
        configs = [
            (s3_destination_configuration, "S3"),
            (extended_s3_destination_configuration, "Extended_S3"),
            (redshift_destination_configuration, "ElasticSearch"),
            (elasticsearch_destination_configuration, "Redshift"),
            (splunk_destination_configuration, "Splunk"),
            (http_endpoint_destination_configuration, "Http"),
        ]
        non_null_configs = [bool(x[0]) for x in configs]
        if non_null_configs.count(True) != 1:
            raise InvalidArgumentException(
                "Exactly one destination configuration is supported for a Firehose"
            )
        dest_config = configs[non_null_configs.index(True)]
        destination_config = dest_config[0]
        destination_type = dest_config[1]

        self.delivery_streams[delivery_stream_name] = DeliveryStream(
            self.region_name,
            delivery_stream_name,
            delivery_stream_type,
            kinesis_stream_source_configuration,
            destination_type,
            destination_config,
            tags,
        )
        return self.delivery_streams[delivery_stream_name].delivery_stream_arn

    def delete_delivery_stream(self, delivery_stream_name, allow_force_delete=False):
        """Delete a delivery stream and its data"""
        delivery_stream = self.delivery_streams.get(delivery_stream_name)
        if not delivery_stream:
            raise ResourceNotFoundException(delivery_stream_name)

        # TODO - the error message below and AllowForceDelete

        # The following logic is not applicable for moto as far as I can tell.
        # if delivery_stream.state == "CREATING":
        #     raise ResourceInUseException(
        #         f"The rule {rule_name} is currently being deleted.  Please "
        #         f"retry after some time"
        #     )
        delivery_stream.state = "DELETING"
        self.delivery_streams.pop(delivery_stream_name)

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

        # If a starting delivery stream name was given, find the index into
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
