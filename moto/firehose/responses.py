"""Handles Firehose API requests, invokes method and returns response."""
import json

from moto.core.responses import BaseResponse
from .models import firehose_backends


class FirehoseResponse(BaseResponse):

    """Handler for Firehose requests and responses."""

    @property
    def firehose_backend(self):
        """Return backend instance specific to this region."""
        return firehose_backends[self.region]

    def create_delivery_stream(self):
        """Prepare argumenst and respond to CreateDeliveryStream request."""
        delivery_stream_arn = self.firehose_backend.create_delivery_stream(
            self._get_param("DeliveryStreamName"),
            self._get_param("DeliveryStreamType"),
            self._get_param("KinesisStreamSourceConfiguration"),
            self._get_param("DeliveryStreamEncryptionConfigurationInput"),
            self._get_param("S3DestinationConfiguration"),
            self._get_param("ExtendedS3DestinationConfiguration"),
            self._get_param("RedshiftDestinationConfiguration"),
            self._get_param("ElasticsearchDestinationConfiguration"),
            self._get_param("SplunkDestinationConfiguration"),
            self._get_param("HttpEndpointDestinationConfiguration"),
            self._get_list_prefix("Tags.member"),
        )
        return json.dumps(dict(deliveryStreamArn=delivery_stream_arn))

    def delete_delivery_stream(self):
        """Prepare argumenst and respond to DeleteDeliveryStream request."""
        self.firehose_backend.delete_delivery_stream(
            delivery_stream_name = self._get_param("DeliveryStreamName"),
            allow_force_delete = self._get_param("AllowForceDelete"),
        )
        return json.dumps(dict())
