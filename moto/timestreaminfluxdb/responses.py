import json

from moto.core.responses import BaseResponse

from .models import (
    DBStorageType,
    DeploymentType,
    NetworkType,
    TimestreamInfluxDBBackend,
    timestreaminfluxdb_backends,
)


class TimestreamInfluxDBResponse(BaseResponse):
    """Handler for TimestreamInfluxDB requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="timestream-influxdb")

    @property
    def timestreaminfluxdb_backend(self) -> TimestreamInfluxDBBackend:
        return timestreaminfluxdb_backends[self.current_account][self.region]

    def create_db_instance(self) -> str:
        params = json.loads(self.body)
        name = params.get("name")
        username = params.get("username")
        password = params.get("password")
        organization = params.get("organization")
        bucket = params.get("bucket")
        db_instance_type = params.get("dbInstanceType")
        vpc_subnet_ids = params.get("vpcSubnetIds")
        vpc_security_group_ids = params.get("vpcSecurityGroupIds")
        publicly_accessible = params.get("publiclyAccessible", False)
        db_storage_type = params.get("dbStorageType", DBStorageType.InfluxIOIncludedT1)
        allocated_storage = params.get("allocatedStorage")
        db_parameter_group_identifier = params.get("dbParameterGroupIdentifier")
        deployment_type = params.get("deploymentType", DeploymentType.SINGLE_AZ)
        log_delivery_configuration = params.get("logDeliveryConfiguration", {})
        tags = params.get("tags", {})
        port = int(params.get("port", 8086))
        network_type = params.get("networkType", NetworkType.IPV4)

        created_instance = self.timestreaminfluxdb_backend.create_db_instance(
            name=name,
            username=username,
            password=password,
            organization=organization,
            bucket=bucket,
            db_instance_type=db_instance_type,
            vpc_subnet_ids=vpc_subnet_ids,
            vpc_security_group_ids=vpc_security_group_ids,
            publicly_accessible=publicly_accessible,
            db_storage_type=db_storage_type,
            allocated_storage=allocated_storage,
            db_parameter_group_identifier=db_parameter_group_identifier,
            deployment_type=deployment_type,
            log_delivery_configuration=log_delivery_configuration,
            tags=tags,
            port=port,
            network_type=network_type,
        )
        return json.dumps(created_instance.to_dict())

    def delete_db_instance(self) -> str:
        params = json.loads(self.body)
        id = params.get("identifier")
        deleted_instance = self.timestreaminfluxdb_backend.delete_db_instance(id=id)
        return json.dumps(deleted_instance.to_dict())

    def get_db_instance(self) -> str:
        params = json.loads(self.body)
        id = params.get("identifier")
        instance = self.timestreaminfluxdb_backend.get_db_instance(id=id)
        return json.dumps(instance.to_dict())

    def list_db_instances(self) -> str:
        """
        Pagination is not yet implemented
        """
        instances = self.timestreaminfluxdb_backend.list_db_instances()

        return json.dumps({"items": instances})

    def tag_resource(self) -> str:
        params = json.loads(self.body)
        arn = params.get("resourceArn")
        tags = params.get("tags")
        self.timestreaminfluxdb_backend.tag_resource(resource_arn=arn, tags=tags)
        return "{}"

    def untag_resource(self) -> str:
        params = json.loads(self.body)
        arn = params.get("resourceArn")
        tag_keys = params.get("tagKeys")
        self.timestreaminfluxdb_backend.untag_resource(
            resource_arn=arn, tag_keys=tag_keys
        )
        return "{}"

    def list_tags_for_resource(self) -> str:
        params = json.loads(self.body)
        arn = params.get("resourceArn")
        tags = self.timestreaminfluxdb_backend.list_tags_for_resource(resource_arn=arn)
        return json.dumps({"tags": tags})
