"""Handles incoming mq requests, invokes methods, returns responses."""

import copy

from moto.core.responses import ActionResult, BaseResponse, EmptyResult, PaginatedResult

from .models import MQBackend, mq_backends


class MQResponse(BaseResponse):
    """Handler for MQ requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="mq")
        self.automated_parameter_parsing = True

    @property
    def mq_backend(self) -> MQBackend:
        """Return backend instance specific for this region."""
        return mq_backends[self.current_account][self.region]

    def create_broker(self) -> ActionResult:
        authentication_strategy = self._get_param("AuthenticationStrategy")
        auto_minor_version_upgrade = self._get_bool_param("AutoMinorVersionUpgrade")
        broker_name = self._get_param("BrokerName")
        configuration = self._get_param("Configuration")
        deployment_mode = self._get_param("DeploymentMode")
        encryption_options = self._get_param("EncryptionOptions")
        engine_type = self._get_param("EngineType")
        engine_version = self._get_param("EngineVersion")
        host_instance_type = self._get_param("HostInstanceType")
        ldap_server_metadata = self._get_param("LdapServerMetadata")
        logs = self._get_param("Logs", {})
        maintenance_window_start_time = self._get_param("MaintenanceWindowStartTime")
        publicly_accessible = self._get_bool_param("PubliclyAccessible")
        security_groups = self._get_param("SecurityGroups")
        storage_type = self._get_param("StorageType")
        subnet_ids = self._get_param("SubnetIds", [])
        tags = self._get_param("Tags")
        users = self._get_param("Users", [])
        broker_arn, broker_id = self.mq_backend.create_broker(
            authentication_strategy=authentication_strategy,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            broker_name=broker_name,
            configuration=configuration,
            deployment_mode=deployment_mode,
            encryption_options=encryption_options,
            engine_type=engine_type,
            engine_version=engine_version,
            host_instance_type=host_instance_type,
            ldap_server_metadata=ldap_server_metadata,
            logs=logs,
            maintenance_window_start_time=maintenance_window_start_time,
            publicly_accessible=publicly_accessible,
            security_groups=security_groups,
            storage_type=storage_type,
            subnet_ids=subnet_ids,
            tags=tags,
            users=users,
        )
        resp = {"brokerArn": broker_arn, "brokerId": broker_id}
        return ActionResult(resp)

    def update_broker(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        authentication_strategy = self._get_param("AuthenticationStrategy")
        auto_minor_version_upgrade = self._get_bool_param("AutoMinorVersionUpgrade")
        configuration = self._get_param("Configuration")
        engine_version = self._get_param("EngineVersion")
        host_instance_type = self._get_param("HostInstanceType")
        ldap_server_metadata = self._get_param("LdapServerMetadata")
        logs = self._get_param("Logs")
        maintenance_window_start_time = self._get_param("MaintenanceWindowStartTime")
        security_groups = self._get_param("SecurityGroups")
        self.mq_backend.update_broker(
            authentication_strategy=authentication_strategy,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            broker_id=broker_id,
            configuration=configuration,
            engine_version=engine_version,
            host_instance_type=host_instance_type,
            ldap_server_metadata=ldap_server_metadata,
            logs=logs,
            maintenance_window_start_time=maintenance_window_start_time,
            security_groups=security_groups,
        )
        return self.describe_broker()

    def delete_broker(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        self.mq_backend.delete_broker(broker_id=broker_id)
        return ActionResult({"BrokerId": broker_id})

    def describe_broker(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        broker = self.mq_backend.describe_broker(broker_id=broker_id)
        resp = copy.copy(broker)
        resp.tags = self.mq_backend.list_tags(broker.arn)  # type: ignore[attr-defined]
        return ActionResult(resp)

    def list_brokers(self) -> ActionResult:
        brokers = self.mq_backend.list_brokers()
        return ActionResult({"BrokerSummaries": brokers})

    def create_user(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        username = self._get_param("Username")
        console_access = self._get_bool_param("ConsoleAccess", False)
        groups = self._get_param("Groups", [])
        self.mq_backend.create_user(broker_id, username, console_access, groups)
        return EmptyResult()

    def update_user(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        username = self._get_param("Username")
        console_access = self._get_bool_param("ConsoleAccess", False)
        groups = self._get_param("Groups", [])
        self.mq_backend.update_user(
            broker_id=broker_id,
            console_access=console_access,
            groups=groups,
            username=username,
        )
        return EmptyResult()

    def describe_user(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        username = self._get_param("Username")
        user = self.mq_backend.describe_user(broker_id, username)
        return ActionResult(user)

    def delete_user(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        username = self._get_param("Username")
        self.mq_backend.delete_user(broker_id, username)
        return EmptyResult()

    def list_users(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        users = self.mq_backend.list_users(broker_id=broker_id)
        resp = {
            "brokerId": broker_id,
            "users": [{"username": u.username} for u in users],
        }
        return ActionResult(resp)

    def create_configuration(self) -> ActionResult:
        name = self._get_param("Name")
        engine_type = self._get_param("EngineType")
        engine_version = self._get_param("EngineVersion")
        tags = self._get_param("Tags", {})

        config = self.mq_backend.create_configuration(
            name, engine_type, engine_version, tags
        )
        return ActionResult(config)

    def describe_configuration(self) -> ActionResult:
        config_id = self._get_param("ConfigurationId")
        config = self.mq_backend.describe_configuration(config_id)
        resp = copy.copy(config)
        resp.tags = self.mq_backend.list_tags(config.arn)  # type: ignore[attr-defined]
        return ActionResult(resp)

    def list_configurations(self) -> ActionResult:
        configs = self.mq_backend.list_configurations()
        resp = {"Configurations": configs}
        return ActionResult(resp)

    def delete_configuration(self) -> ActionResult:
        config_id = self.path.split("/")[-1]
        self.mq_backend.delete_configuration(config_id)
        return ActionResult({"ConfigurationId": config_id})

    def list_configuration_revisions(self) -> ActionResult:
        config_id = self.path.split("/")[-2]
        revisions = self.mq_backend.list_configuration_revisions(config_id=config_id)
        resp = {
            "ConfigurationId": config_id,
            "MaxResults": self._get_int_param("MaxResults"),
            "Revisions": revisions,
        }
        return PaginatedResult(resp)

    def update_configuration(self) -> ActionResult:
        config_id = self._get_param("ConfigurationId")
        data = self._get_param("Data")
        description = self._get_param("Description")
        config = self.mq_backend.update_configuration(config_id, data, description)
        return ActionResult(config)

    def describe_configuration_revision(self) -> ActionResult:
        revision_id = self._get_param("ConfigurationRevision")
        config_id = self._get_param("ConfigurationId")
        revision = self.mq_backend.describe_configuration_revision(
            config_id, revision_id
        )
        return ActionResult(revision)

    def create_tags(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags", {})
        self.mq_backend.create_tags(resource_arn, tags)
        return EmptyResult()

    def delete_tags(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.mq_backend.delete_tags(resource_arn, tag_keys)
        return EmptyResult()

    def list_tags(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self.mq_backend.list_tags(resource_arn)
        return ActionResult({"Tags": tags})

    def reboot_broker(self) -> ActionResult:
        broker_id = self._get_param("BrokerId")
        self.mq_backend.reboot_broker(broker_id=broker_id)
        return EmptyResult()

    def describe_shared_resources(self) -> ActionResult:
        return ActionResult(result={"SharedResources": []})
