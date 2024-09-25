"""OpenSearchIngestionBackend class with methods for supported APIs."""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

import yaml

from moto.core.base_backend import BackendDict, BaseBackend
from moto.ec2 import ec2_backends
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.ec2.models import EC2Backend
from moto.moto_api._internal import mock_random as random
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.opensearch import opensearch_backends
from moto.opensearch.exceptions import ResourceNotFoundException
from moto.opensearch.models import OpenSearchServiceBackend
from moto.opensearchserverless import opensearchserverless_backends
from moto.opensearchserverless.models import OpenSearchServiceServerlessBackend
from moto.utilities.paginator import paginate
from moto.utilities.utils import get_partition

from .exceptions import (
    InvalidVPCOptionsException,
    PipelineAlreadyExistsException,
    PipelineInvalidStateException,
    PipelineNotFoundException,
    PipelineValidationException,
    SecurityGroupNotFoundException,
    SubnetNotFoundException,
)


class Pipeline(ManagedState):
    VALID_BUFFERING_SOURCES: ClassVar[List[str]] = [
        "http",
        "otel_metrics_source",
        "otel_trace_source",
        "otel_logs_source",
    ]
    CREATING_REASON: ClassVar[str] = (
        "The pipeline is being created. It is not able to ingest data."
    )
    ACTIVE_NO_ENDPOINT_REASON: ClassVar[str] = (
        'WARN: There is no "available" VPC endpoint associated with this pipeline. You must configure an interface vpc endpoint to ingest data.'
    )
    ACTIVE_REASON: ClassVar[str] = "The pipeline is ready to ingest data."
    DELETING_REASON: ClassVar[str] = "The pipeline is being deleted"
    STOPPING_REASON: ClassVar[str] = "The pipeline is being stopped"
    STOPPED_REASON: ClassVar[str] = "The pipeline is stopped"
    STARTING_REASON: ClassVar[str] = (
        "The pipeline is starting. It is not able to ingest data"
    )
    UPDATING_REASON: ClassVar[str] = (
        "An update was triggered for the pipeline. It is still available to ingest data."
    )

    STATUS_REASON_MAP: ClassVar[Dict[str, str]] = {
        "CREATING": CREATING_REASON,
        "ACTIVE": ACTIVE_REASON,
        "STOPPING": STOPPING_REASON,
        "STOPPED": STOPPED_REASON,
        "STARTING": STARTING_REASON,
        "UPDATING": UPDATING_REASON,
        "DELETING": DELETING_REASON,
    }

    def __init__(
        self,
        pipeline_name,
        account_id,
        region,
        min_units,
        max_units,
        pipeline_configuration_body,
        log_publishing_options,
        vpc_options,
        buffer_options,
        encryption_at_rest_options,
        tags,
        ingest_endpoint_urls,
        serverless,
        vpc_endpoint_service,
    ):
        ManagedState.__init__(
            self,
            model_name="osis::pipeline",
            transitions=[
                ("CREATING", "ACTIVE"),
                ("UPDATING", "ACTIVE"),
                ("DELETING", "DELETED"),
                ("STOPPING", "STOPPED"),
                ("STOPPED", "STARTING"),
                ("STARTING", "ACTIVE"),
            ],
        )

        self.pipeline_name = pipeline_name
        self.account_id = account_id
        self.region = region
        self.min_units = min_units
        self.max_units = max_units
        self.pipeline_configuration_body_str = pipeline_configuration_body
        self.pipeline_configuration_body = yaml.safe_load(pipeline_configuration_body)
        self.log_publishing_options = log_publishing_options
        self.vpc_options = vpc_options
        self.buffer_options = buffer_options
        self.encryption_at_rest_options = encryption_at_rest_options
        self.tags = tags
        self.ingest_endpoint_urls = ingest_endpoint_urls
        self.serverless = serverless
        self.vpc_endpoint_service = vpc_endpoint_service

        self._validate_buffer_options()
        self.arn = self._get_arn(self.pipeline_name)
        self.destinations = self._update_destinations()
        if self.vpc_options is not None:
            self.vpc_endpoint = self.vpc_options.get("VpcEndpointId")
        else:
            self.vpc_endpoint = None

        if (
            self.vpc_options is None or self.vpc_options.get("VpcEndpointManagement", "SERVICE") == "SERVICE"
        ):
            self.vpc_endpoint_service = None
        else:
            # Not returned when VpcEndpointManagement is CUSTOMER even if one has been created
            self.vpc_options["VpcEndpointId"] = None

        self.service_vpc_endpoints = self._get_service_vpc_endpoints()
        self.created_at: datetime = datetime.now()
        self.last_updated_at: datetime = datetime.now()

    def _get_arn(self, name: str) -> str:
        return f"arn:{get_partition(self.region)}:osis:{self.region}:{self.account_id}:pipeline/{name}"

    def _get_service_vpc_endpoints(self) -> List[Dict[str, str]]:
        # ServiceVpcEndpoint.VpcEndpointId not implemented
        if self.serverless:
            return [{"ServiceName": "OPENSEARCH_SERVERLESS"}]
        else:
            return None

    def _get_status_reason(self) -> str:
        if self.vpc_endpoint is None and self.vpc_options is not None and self.status == "ACTIVE":
            return self.ACTIVE_NO_ENDPOINT_REASON

        return self.STATUS_REASON_MAP.get(self.status)

    def _update_destinations(self) -> List[Dict[str, str]]:
        destinations = []
        for sub_pipeline in self.pipeline_configuration_body:
            if sub_pipeline != "version":
                for sink in self.pipeline_configuration_body[sub_pipeline]["sink"]:
                    for sink_type, sink_config in sink.items():
                        if sink_type == "opensearch":
                            if sink_config["aws"].get("serverless") is True:
                                service_name = "OpenSearch_Serverless"
                            else:
                                service_name = "OpenSearch"
                            endpoint = sink_config["hosts"][0]
                        elif sink_type == "s3":
                            service_name = "S3"
                            endpoint = sink_config["bucket"]
                        else:
                            continue
                        destinations.append(
                            {"ServiceName": service_name, "Endpoint": endpoint}
                        )
        return destinations

    def _validate_buffer_options(self) -> None:
        if self.buffer_options is not None and self.buffer_options.get("PersistentBufferEnabled", False) is True:
            for sub_pipeline in self.pipeline_configuration_body:
                if sub_pipeline != "version":
                    source = self.pipeline_configuration_body[sub_pipeline]["source"]
                    source_type = list(source.keys())[0]
                    if source_type not in self.VALID_BUFFERING_SOURCES:
                        raise PipelineValidationException(
                            f"Persistent buffering is only supported for the following source types: {self.VALID_BUFFERING_SOURCES}"
                        )

    @staticmethod
    def _is_serverless(config: Dict[str, Any]) -> bool:
        return config.get("aws", {}).get("serverless", False)

    @classmethod
    def _check_opensearch_exists(
        cls, pipeline_account_id: str, sink_config: Dict[str, Any]
    ) -> None:
        if sink_config["aws"].get("serverless") is True:
            collection_id = sink_config["hosts"][0].split("://")[1].split(".")[0]
            region = sink_config["hosts"][0].split(".")[1]
            if (
                cls.get_oss_backend(pipeline_account_id, region).batch_get_collection(
                    ids=[collection_id], names=[]
                )[1]
                != []
            ):
                raise PipelineValidationException(
                    f"OpenSearch Serverless collection {sink_config['hosts'][0]} not found."
                )
        else:
            domain_name = sink_config["hosts"][0].split("-")[1]
            try:
                cls.get_opensearch_backend(pipeline_account_id, region).describe_domain(
                    DomainName=domain_name
                )
            except ResourceNotFoundException:
                raise PipelineValidationException(
                    f"OpenSearch domain {sink_config['hosts'][0]} not found."
                )

    @classmethod
    def parse_opensearch(
        cls, pipeline_account_id: str, pipeline_body: Dict[str, Any]
    ) -> bool:
        # Validate if any OpenSearch resources serverless and validate Opensearch sinks exits
        serverless = False
        for sub_pipeline in pipeline_body:
            if sub_pipeline != "version":
                for sink in pipeline_body[sub_pipeline]["sink"]:
                    for sink_type, sink_config in sink.items():
                        if sink_type == "opensearch":
                            cls._check_opensearch_exists(
                                pipeline_account_id, sink_config
                            )
                            serverless = cls._is_serverless(sink_config) or serverless
                source_type = list(pipeline_body[sub_pipeline]["source"].keys())[0]
                if source_type == "opensearch":
                    source_config = pipeline_body[sub_pipeline]["source"][source_type]
                    serverless = cls._is_serverless(source_config) or serverless
        return serverless

    def delete(self):
        self.status = "DELETING"
        self.set_last_updated()

    def get_created_at(self) -> str:
        return self.created_at.astimezone().isoformat()

    def get_last_updated_at(self) -> str:
        return self.last_updated_at.astimezone().isoformat()

    @staticmethod
    def get_oss_backend(account_id, region) -> OpenSearchServiceServerlessBackend:  # type: ignore[misc]
        return opensearchserverless_backends[account_id][region]

    @staticmethod
    def get_opensearch_backend(account_id, region) -> OpenSearchServiceBackend:  # type: ignore[misc]
        return opensearch_backends[account_id][region]

    def set_last_updated(self):
        self.last_updated_at = datetime.now()

    def stop(self):
        self.status = "STOPPING"
        self.set_last_updated()

    def to_dict(self):
        return {
            "PipelineName": self.pipeline_name,
            "PipelineArn": self.arn,
            "MinUnits": self.min_units,
            "MaxUnits": self.max_units,
            "Status": self.status,
            "StatusReason": {
                "Description": self._get_status_reason(),
            },
            "PipelineConfigurationBody": self.pipeline_configuration_body_str,
            "CreatedAt": self.get_created_at(),
            "LastUpdatedAt": self.get_last_updated_at(),
            "IngestEndpointUrls": self.ingest_endpoint_urls,
            "LogPublishingOptions": self.log_publishing_options,
            "VpcEndpoints": None if self.vpc_options is None else [self.vpc_options],
            "BufferOptions": self.buffer_options,
            "EncryptionAtRestOptions": self.encryption_at_rest_options,
            "VpcEndpointService": self.vpc_endpoint_service,
            "ServiceVpcEndpoints": self.service_vpc_endpoints,
            "VpcOptions": self.vpc_options,
            "Destinations": self.destinations,
            "Tags": self.tags,
        }

    def to_short_dict(self):
        return {
            "Status": self.status,
            "StatusReason": self._get_status_reason(),
            "PipelineName": self.pipeline_name,
            "PipelineArn": self.arn,
            "MinUnits": self.min_units,
            "MaxUnits": self.max_units,
            "CreatedAt": self.get_created_at(),
            "LastUpdatedAt": self.get_last_updated_at(),
            "Destinations": self.destinations,
            "Tags": self.tags,
        }

    def update(
        self,
        min_units,
        max_units,
        pipeline_configuration_body,
        log_publishing_options,
        buffer_options,
        encryption_at_rest_options,
    ) -> None:
        self.min_units = min_units
        self.max_units = max_units
        self.pipeline_configuration_body = self.load_pipeline_body(
            pipeline_configuration_body
        )
        self._validate_buffer_options()
        self.serverless = self.parse_opensearch(
            self.account_id, self.pipeline_configuration_body
        )
        self.log_publishing_options = log_publishing_options
        self.buffer_options = buffer_options
        self.encryption_at_rest_options = encryption_at_rest_options
        self._update_destinations()
        self.service_vpc_endpoints = self._get_service_vpc_endpoints()
        self.status = "UPDATING"
        self.set_last_updated()


class OpenSearchIngestionBackend(BaseBackend):
    """Implementation of OpenSearchIngestion APIs."""

    PAGINATION_MODEL = {
        "list_resources": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "PipelineName",
        },
    }

    PIPELINE_DELETE_VALID_STATES = [
        "UPDATE_FAILED",
        "ACTIVE",
        "START_FAILED",
        "STOPPED",
        "CREATE_FAILED",
    ]
    PIPELINE_STOP_VALID_STATES = ["UPDATE_FAILED", "ACTIVE"]
    PIPELINE_START_VALID_STATES = ["START_FAILED", "STOPPED"]
    PIPELINE_UPDATE_VALID_STATES = [
        "UPDATE_FAILED",
        "ACTIVE",
        "START_FAILED",
        "STOPPED",
    ]

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._pipelines: Dict[str, Pipeline] = dict()

    @property
    def ec2_backend(self) -> EC2Backend:  # type: ignore[misc]
        return ec2_backends[self.account_id][self.region_name]

    @property
    def pipelines(self) -> Dict[str, Pipeline]:
        self._pipelines = {
            name: pipeline
            for name, pipeline in self._pipelines.items()
            if pipeline.status != "DELETED"
        }
        return self._pipelines

    def _get_ingest_endpoint_urls(
        self, pipeline_name: str, endpoint_random_string: str
    ) -> List[str]:
        return [
            f"{pipeline_name}-{endpoint_random_string}.{self.region_name}.osis.amazonaws.com"
        ]

    def _get_random_endpoint_string(self) -> str:
        return random.get_random_string(length=26, lower_case=True)

    def _get_vpc_endpoint(
        self, vpc_options: Dict[str, Any], service_name: str
    ) -> Optional[str]:
        if vpc_options.get("VpcEndpointManagement", "SERVICE") == "SERVICE":
            service_managed_endpoint = self.ec2_backend.create_vpc_endpoint(
                vpc_id=vpc_options["VpcId"],
                service_name=service_name,
                endpoint_type="Interface",
                security_group_ids=vpc_options.get("SecurityGroupIds"),
                subnet_ids=vpc_options["SubnetIds"],
                private_dns_enabled=False,
                tags={"OSISManaged": "true"},
            )
            return service_managed_endpoint.id
        else:
            endpoints = (
                self.ec2_backend.describe_vpc_endpoints(
                    Filters=[{"Name": "service-name", "Values": [service_name]}]
                )["VpcEndpoints"]
                != []
            )
            if endpoints != []:
                return endpoints[0]["VpcEndpointId"]
            else:
                return None

    def _get_vpc_endpoint_service(
        self, pipeline_name: str, endpoint_random_string: str
    ) -> str:
        f"com.amazonaws.osis.{self.region_name}.{pipeline_name}-{endpoint_random_string}"

    def _validate_and_get_vpc(self, vpc_options: Dict[str, Any]) -> str:
        vpc_id = None
        for subnet_id in vpc_options["SubnetIds"]:
            try:
                subnet = self.ec2_backend.get_subnet(subnet_id)
            except InvalidSubnetIdError:
                # re-raising for more accurate error message
                raise SubnetNotFoundException(subnet_id)
            if vpc_id is None:
                vpc_id = subnet.vpc_id
            else:
                if subnet.vpc_id != vpc_id:
                    raise InvalidVPCOptionsException(
                        "All specified subnets must belong to the same VPC."
                    )

        for sg_id in vpc_options["SecurityGroupIds"]:
            sg = self.ec2_backend.get_security_group_from_id(sg_id)
            if sg is None:
                raise SecurityGroupNotFoundException(sg_id)

        return vpc_id

    def create_pipeline(
        self,
        pipeline_name: str,
        min_units: int,
        max_units: int,
        pipeline_configuration_body: str,
        log_publishing_options: Optional[Dict[str, Any]],
        vpc_options: Optional[Dict[str, Any]],
        buffer_options: Optional[Dict[str, bool]],
        encryption_at_rest_options: Optional[Dict[str, Any]],
        tags: List[Dict[str, str]],
    ) -> Pipeline:
        if pipeline_name in self.pipelines:
            raise PipelineAlreadyExistsException(pipeline_name)

        serverless = Pipeline.parse_opensearch(self.account_id, yaml.safe_load(pipeline_configuration_body))

        endpoint_random_string = self._get_random_endpoint_string()
        endpoint_service = self._get_vpc_endpoint_service(pipeline_name, endpoint_random_string)
        ingestion_endpoint_urls = self._get_ingest_endpoint_urls(
            pipeline_name, endpoint_random_string
        )
        if vpc_options is not None:
            vpc_options["VpcId"] = self._validate_and_get_vpc(vpc_options)
            vpc_options["VpcEndpointId"] = self._get_vpc_endpoint(
                vpc_options, endpoint_service
            )

        pipeline = Pipeline(
            pipeline_name,
            self.account_id,
            self.region_name,
            min_units,
            max_units,
            pipeline_configuration_body,
            log_publishing_options,
            vpc_options,
            buffer_options,
            encryption_at_rest_options,
            tags,
            ingestion_endpoint_urls,
            serverless,
            endpoint_service,
        )
        self.pipelines[pipeline_name] = pipeline
        return pipeline

    def delete_pipeline(self, pipeline_name: str) -> None:
        if pipeline_name not in self.pipelines:
            raise PipelineNotFoundException(pipeline_name)
        pipeline = self.pipelines[pipeline_name]
        if pipeline.status not in self.PIPELINE_DELETE_VALID_STATES:
            raise PipelineInvalidStateException(
                "deletion", self.PIPELINE_DELETE_VALID_STATES, pipeline.status
            )
        pipeline.delete()

    def get_pipeline(self, pipeline_name: str) -> Pipeline:
        if pipeline_name not in self.pipelines:
            raise PipelineNotFoundException(pipeline_name)
        pipeline = self.pipelines[pipeline_name]
        pipeline.advance()
        return pipeline

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_pipelines(self) -> List[Dict[str, Any]]:
        for pipeline in self.pipelines.values():
            pipeline.advance()
        return [p.to_short_dict() for p in self.pipelines.values()]

    def list_tags_for_resource(self, arn):
        # implement here
        # return tags
        return arn

    def update_pipeline(
        self,
        pipeline_name,
        min_units,
        max_units,
        pipeline_configuration_body,
        log_publishing_options,
        buffer_options,
        encryption_at_rest_options,
    ):
        if pipeline_name not in self.pipelines:
            raise PipelineNotFoundException(pipeline_name)
        pipeline = self.pipelines[pipeline_name]
        if pipeline.status not in self.PIPELINE_UPDATE_VALID_STATES:
            raise PipelineInvalidStateException(
                "updates", self.PIPELINE_UPDATE_VALID_STATES, pipeline.status
            )
        pipeline.update(
            min_units,
            max_units,
            pipeline_configuration_body,
            log_publishing_options,
            buffer_options,
            encryption_at_rest_options,
        )
        return pipeline

    def tag_resource(self, arn, tags):
        # implement here
        return

    def untag_resource(self, arn, tag_keys):
        # implement here
        return


osis_backends = BackendDict(OpenSearchIngestionBackend, "osis")
