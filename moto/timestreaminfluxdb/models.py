"""TimestreamInfluxDBBackend class with methods for supported APIs."""

from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import CloudFormationModel

from .utils import validate_name


class DBInstance(CloudFormationModel):
    def __init__(
        self,
        name: str,
        username: Optional[str],
        password: str,
        organization: str,
        bucket: str,
        dbInstanceType: str,
        vpcSubnetIds: List[str],
        vpcSecurityGroupIds: List[str],
        publiclyAccessible: bool,
        dbStorageType: str,
        allocatedStorage: int,
        dbParameterGroupIdentifier: str,
        deploymentType: str,
        logDeliveryConfiguration: Dict[str, Any],
        tags: Dict[str, Any],
        port: int,
        networkType: str,
    ):
        self.name = name
        self.username = username
        self.password = password
        self.organization = organization
        self.bucket = bucket
        self.dbInstanceType = dbInstanceType
        self.vpcSubnetIds = vpcSubnetIds
        self.vpcSecurityGroupIds = vpcSecurityGroupIds
        self.publiclyAccessible = publiclyAccessible
        self.dbStorageType = dbStorageType
        self.allocatedStorage = allocatedStorage
        self.dbParameterGroupIdentifier = dbParameterGroupIdentifier
        self.deploymentType = deploymentType
        self.logDeliveryConfiguration = logDeliveryConfiguration
        self.tags = tags
        self.port = port
        self.networkType = networkType

    @staticmethod
    def cloudformation_name_type() -> str:
        return "Name"

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-timestream-influxdbinstance.html
        return "AWS::Timestream::InfluxDBInstance"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "DBInstance":
        properties = cloudformation_json["Properties"]
        # This must be implemented as a classmethod with parameters:
        # cls, resource_name, cloudformation_json, account_id, region_name
        # Extract the resource parameters from the cloudformation json
        # and return an instance of the resource class

        timestreaminfluxdb_backend = timestreaminfluxdb_backends[account_id][
            region_name
        ]
        return timestreaminfluxdb_backend.create_db_instance(
            name=resource_name, **properties
        )


class TimestreamInfluxDBBackend(BaseBackend):
    """Implementation of TimestreamInfluxDB APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)

    def create_db_instance(
        self,
        name: str,
        username: str,
        password: str,
        organization: str,
        bucket: str,
        db_instance_type: str,
        vpc_subnet_ids: List[str],
        vpc_security_group_ids: List[str],
        publicly_accessible: bool,
        db_storage_type: str,
        allocated_storage: int,
        db_parameter_group_identifier: Optional[str],
        deployment_type: str,
        log_delivery_configuration: Optional[Dict[str, Any]],
        tags: Optional[Dict[str, str]],
        port: int,
        network_type: str,
    ) -> DBInstance:
        # Botocore will check that the specified security groups are valid and must exist.
        # botocore.errorfactory.ValidationException: An error occurred (ValidationException)
        # when calling the CreateDbInstance operation: Nonexistent subnet(s) found in
        # [subnet-0123456789abcdef0]. Your specified subnet(s) must exist.

        print("ASKSLMAS")
        validate_name(name)

        return DBInstance(
            name,
            username,
            password,
            organization,
            bucket,
            db_instance_type,
            vpc_subnet_ids,
            vpc_security_group_ids,
            publicly_accessible,
            db_storage_type,
            allocated_storage,
            db_parameter_group_identifier,
            deployment_type,
            log_delivery_configuration,
            tags,
            port,
            network_type,
        )

    def delete_db_instance(self, name):
        pass

    def get_db_instance(self, name):
        pass

    def list_db_instances(self):
        pass

    def tag_resource(self, name, tags):
        pass

    def untag_resource(self, name, tag_keys):
        pass

    def list_tags_for_resource(self, name):
        pass


timestreaminfluxdb_backends = BackendDict(
    TimestreamInfluxDBBackend, "timestream-influxdb"
)
