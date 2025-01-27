from moto.core.responses import BaseResponse

from .models import TimestreamInfluxDBBackend, timestreaminfluxdb_backends


class TimestreamInfluxDBResponse(BaseResponse):
    """Handler for TimestreamInfluxDB requests and responses."""

    def __init__(self):
        super().__init__(service_name="timestream-influxdb")

    @property
    def timestreaminfluxdb_backend(self) -> TimestreamInfluxDBBackend:
        return timestreaminfluxdb_backends[self.current_account][self.region]

    # add methods from here

    def create_db_instance(self):
        params = self._get_params()
        name = params.get("name")
        username = params.get("username")
        password = params.get("password")
        organization = params.get("organization")
        bucket = params.get("bucket")
        db_instance_type = params.get("dbInstanceType")
        vpc_subnet_ids = params.get("vpcSubnetIds")
        vpc_security_group_ids = params.get("vpcSecurityGroupIds")
        publicly_accessible = params.get("publiclyAccessible")
        db_storage_type = params.get("dbStorageType")
        allocated_storage = params.get("allocatedStorage")
        db_parameter_group_identifier = params.get("dbParameterGroupIdentifier")
        deployment_type = params.get("deploymentType")
        log_delivery_configuration = params.get("logDeliveryConfiguration")
        tags = params.get("tags")
        port = params.get("port")
        network_type = params.get("networkType")

        result = self.timestreaminfluxdb_backend.create_db_instance(
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

        return result


# add templates from here
