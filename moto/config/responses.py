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

    def put_configuration_aggregator(self):
        aggregator = self.config_backend.put_configuration_aggregator(json.loads(self.body), self.region)
        schema = {'ConfigurationAggregator': aggregator}
        return json.dumps(schema)

    def describe_configuration_aggregators(self):
        aggregators = self.config_backend.describe_configuration_aggregators(self._get_param('ConfigurationAggregatorNames'),
                                                                             self._get_param('NextToken'),
                                                                             self._get_param('Limit'))
        return json.dumps(aggregators)

    def delete_configuration_aggregator(self):
        self.config_backend.delete_configuration_aggregator(self._get_param('ConfigurationAggregatorName'))
        return ""

    def put_aggregation_authorization(self):
        agg_auth = self.config_backend.put_aggregation_authorization(self.region,
                                                                     self._get_param('AuthorizedAccountId'),
                                                                     self._get_param('AuthorizedAwsRegion'),
                                                                     self._get_param('Tags'))
        schema = {'AggregationAuthorization': agg_auth}
        return json.dumps(schema)

    def describe_aggregation_authorizations(self):
        authorizations = self.config_backend.describe_aggregation_authorizations(self._get_param('NextToken'), self._get_param('Limit'))

        return json.dumps(authorizations)

    def delete_aggregation_authorization(self):
        self.config_backend.delete_aggregation_authorization(self._get_param('AuthorizedAccountId'), self._get_param('AuthorizedAwsRegion'))

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
