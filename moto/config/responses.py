import json
from moto.core.responses import BaseResponse
from .models import config_backends


class ConfigResponse(BaseResponse):

    @property
    def config_backend(self):
        return config_backends[self.region]

    def put_configuration_recorder(self):
        self.config_backend.put_configuration_recorder(self._get_param('ConfigurationRecorder'))
        return ""

    def describe_configuration_recorders(self):
        recorders = self.config_backend.describe_configuration_recorders(self._get_param('ConfigurationRecorderNames'))
        schema = {'ConfigurationRecorders': recorders}
        return json.dumps(schema)

    def describe_configuration_recorder_status(self):
        recorder_statuses = self.config_backend.describe_configuration_recorder_status(
            self._get_param('ConfigurationRecorderNames'))
        schema = {'ConfigurationRecordersStatus': recorder_statuses}
        return json.dumps(schema)

    def put_delivery_channel(self):
        self.config_backend.put_delivery_channel(self._get_param('DeliveryChannel'))
        return ""

    def describe_delivery_channels(self):
        delivery_channels = self.config_backend.describe_delivery_channels(self._get_param('DeliveryChannelNames'))
        schema = {'DeliveryChannels': delivery_channels}
        return json.dumps(schema)

    def describe_delivery_channel_status(self):
        raise NotImplementedError()

    def delete_delivery_channel(self):
        self.config_backend.delete_delivery_channel(self._get_param('DeliveryChannelName'))
        return ""

    def delete_configuration_recorder(self):
        self.config_backend.delete_configuration_recorder(self._get_param('ConfigurationRecorderName'))
        return ""

    def start_configuration_recorder(self):
        self.config_backend.start_configuration_recorder(self._get_param('ConfigurationRecorderName'))
        return ""

    def stop_configuration_recorder(self):
        self.config_backend.stop_configuration_recorder(self._get_param('ConfigurationRecorderName'))
        return ""
