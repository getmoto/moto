"""For incoming Firehose API requests, invokes method and returns response."""
import json

from moto.core.responses import BaseResponse
from .models import firehose_backends


class FirehoseResponse(BaseResponse):

    """Handler for Firehose requests and responses."""

    @property
    def firehose_backend(self):
        """Return backend for this region."""
        return firehose_backends[self.region]

    def create_delivery_stream(self):
        delivery_stream_name = self._get_param("DeliveryStreamName")
        delivery_stream_type = self._get_param("DeliveryStreamType")
        kinesis_stream_source_configuration = self._get_param(
            "KinesisStreamSourceConfiguration"
        )
        delivery_stream_encryption_configuration_input = self._get_param(
            "DeliveryStreamEncryptionConfigurationInput"
        )
        s3_destination_configuration = self._get_param("S3DestinationConfiguration")
        extended_s3_destination_configuration = self._get_param(
            "ExtendedS3DestinationConfiguration"
        )
        redshift_destination_configuration = self._get_param(
            "RedshiftDestinationConfiguration"
        )
        elasticsearch_destination_configuration = self._get_param(
            "ElasticsearchDestinationConfiguration"
        )
        splunk_destination_configuration = self._get_param(
            "SplunkDestinationConfiguration"
        )
        http_endpoint_destination_configuration = self._get_param(
            "HttpEndpointDestinationConfiguration"
        )
        tags = self._get_list_prefix("Tags.member")
        delivery_stream_arn = self.firehose_backend.create_delivery_stream(
            delivery_stream_name=delivery_stream_name,
            delivery_stream_type=delivery_stream_type,
            kinesis_stream_source_configuration=kinesis_stream_source_configuration,
            delivery_stream_encryption_configuration_input=delivery_stream_encryption_configuration_input,
            s3_destination_configuration=s3_destination_configuration,
            extended_s3_destination_configuration=extended_s3_destination_configuration,
            redshift_destination_configuration=redshift_destination_configuration,
            elasticsearch_destination_configuration=elasticsearch_destination_configuration,
            splunk_destination_configuration=splunk_destination_configuration,
            http_endpoint_destination_configuration=http_endpoint_destination_configuration,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(deliveryStreamArn=delivery_stream_arn))
