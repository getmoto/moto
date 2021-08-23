"""FirehoseBackend class containing methods for supported API calls."""
from boto3 import Session

from moto.config.exceptions import (
    InvalidResourceTypeException,
    InvalidDeliveryFrequency,
)

from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID


class FirehoseBackend(BaseBackend):

    """Implementation of Firehose APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name

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
    ):
        # implement here
        return delivery_stream_arn


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
