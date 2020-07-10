import json
from moto.core.responses import BaseResponse
from .models import config_backends


class ConfigResponse(BaseResponse):
    @property
    def config_backend(self):
        return config_backends[self.region]

    def put_configuration_recorder(self):
        self.config_backend.put_configuration_recorder(
            self._get_param("ConfigurationRecorder")
        )
        return ""

    def put_configuration_aggregator(self):
        aggregator = self.config_backend.put_configuration_aggregator(
            json.loads(self.body), self.region
        )
        schema = {"ConfigurationAggregator": aggregator}
        return json.dumps(schema)

    def describe_configuration_aggregators(self):
        aggregators = self.config_backend.describe_configuration_aggregators(
            self._get_param("ConfigurationAggregatorNames"),
            self._get_param("NextToken"),
            self._get_param("Limit"),
        )
        return json.dumps(aggregators)

    def delete_configuration_aggregator(self):
        self.config_backend.delete_configuration_aggregator(
            self._get_param("ConfigurationAggregatorName")
        )
        return ""

    def put_aggregation_authorization(self):
        agg_auth = self.config_backend.put_aggregation_authorization(
            self.region,
            self._get_param("AuthorizedAccountId"),
            self._get_param("AuthorizedAwsRegion"),
            self._get_param("Tags"),
        )
        schema = {"AggregationAuthorization": agg_auth}
        return json.dumps(schema)

    def describe_aggregation_authorizations(self):
        authorizations = self.config_backend.describe_aggregation_authorizations(
            self._get_param("NextToken"), self._get_param("Limit")
        )

        return json.dumps(authorizations)

    def delete_aggregation_authorization(self):
        self.config_backend.delete_aggregation_authorization(
            self._get_param("AuthorizedAccountId"),
            self._get_param("AuthorizedAwsRegion"),
        )

        return ""

    def describe_configuration_recorders(self):
        recorders = self.config_backend.describe_configuration_recorders(
            self._get_param("ConfigurationRecorderNames")
        )
        schema = {"ConfigurationRecorders": recorders}
        return json.dumps(schema)

    def describe_configuration_recorder_status(self):
        recorder_statuses = self.config_backend.describe_configuration_recorder_status(
            self._get_param("ConfigurationRecorderNames")
        )
        schema = {"ConfigurationRecordersStatus": recorder_statuses}
        return json.dumps(schema)

    def put_delivery_channel(self):
        self.config_backend.put_delivery_channel(self._get_param("DeliveryChannel"))
        return ""

    def describe_delivery_channels(self):
        delivery_channels = self.config_backend.describe_delivery_channels(
            self._get_param("DeliveryChannelNames")
        )
        schema = {"DeliveryChannels": delivery_channels}
        return json.dumps(schema)

    def describe_delivery_channel_status(self):
        raise NotImplementedError()

    def delete_delivery_channel(self):
        self.config_backend.delete_delivery_channel(
            self._get_param("DeliveryChannelName")
        )
        return ""

    def delete_configuration_recorder(self):
        self.config_backend.delete_configuration_recorder(
            self._get_param("ConfigurationRecorderName")
        )
        return ""

    def start_configuration_recorder(self):
        self.config_backend.start_configuration_recorder(
            self._get_param("ConfigurationRecorderName")
        )
        return ""

    def stop_configuration_recorder(self):
        self.config_backend.stop_configuration_recorder(
            self._get_param("ConfigurationRecorderName")
        )
        return ""

    def list_discovered_resources(self):
        schema = self.config_backend.list_discovered_resources(
            self._get_param("resourceType"),
            self.region,
            self._get_param("resourceIds"),
            self._get_param("resourceName"),
            self._get_param("limit"),
            self._get_param("nextToken"),
        )
        return json.dumps(schema)

    def list_aggregate_discovered_resources(self):
        schema = self.config_backend.list_aggregate_discovered_resources(
            self._get_param("ConfigurationAggregatorName"),
            self._get_param("ResourceType"),
            self._get_param("Filters"),
            self._get_param("Limit"),
            self._get_param("NextToken"),
        )
        return json.dumps(schema)

    def get_resource_config_history(self):
        schema = self.config_backend.get_resource_config_history(
            self._get_param("resourceType"), self._get_param("resourceId"), self.region
        )
        return json.dumps(schema)

    def batch_get_resource_config(self):
        schema = self.config_backend.batch_get_resource_config(
            self._get_param("resourceKeys"), self.region
        )
        return json.dumps(schema)

    def batch_get_aggregate_resource_config(self):
        schema = self.config_backend.batch_get_aggregate_resource_config(
            self._get_param("ConfigurationAggregatorName"),
            self._get_param("ResourceIdentifiers"),
        )
        return json.dumps(schema)

    def put_evaluations(self):
        evaluations = self.config_backend.put_evaluations(
            self._get_param("Evaluations"),
            self._get_param("ResultToken"),
            self._get_param("TestMode"),
        )
        return json.dumps(evaluations)

    def put_organization_conformance_pack(self):
        conformance_pack = self.config_backend.put_organization_conformance_pack(
            region=self.region,
            name=self._get_param("OrganizationConformancePackName"),
            template_s3_uri=self._get_param("TemplateS3Uri"),
            template_body=self._get_param("TemplateBody"),
            delivery_s3_bucket=self._get_param("DeliveryS3Bucket"),
            delivery_s3_key_prefix=self._get_param("DeliveryS3KeyPrefix"),
            input_parameters=self._get_param("ConformancePackInputParameters"),
            excluded_accounts=self._get_param("ExcludedAccounts"),
        )

        return json.dumps(conformance_pack)

    def describe_organization_conformance_packs(self):
        conformance_packs = self.config_backend.describe_organization_conformance_packs(
            self._get_param("OrganizationConformancePackNames")
        )

        return json.dumps(conformance_packs)

    def describe_organization_conformance_pack_statuses(self):
        statuses = self.config_backend.describe_organization_conformance_pack_statuses(
            self._get_param("OrganizationConformancePackNames")
        )

        return json.dumps(statuses)

    def get_organization_conformance_pack_detailed_status(self):
        # 'Filters' parameter is not implemented yet
        statuses = self.config_backend.get_organization_conformance_pack_detailed_status(
            self._get_param("OrganizationConformancePackName")
        )

        return json.dumps(statuses)

    def delete_organization_conformance_pack(self):
        self.config_backend.delete_organization_conformance_pack(
            self._get_param("OrganizationConformancePackName")
        )

        return ""
