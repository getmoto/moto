import base64
import xmltodict

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService

from .configuration import DEFAULT_CONFIGURATION_DATA
from .exceptions import (
    UnknownBroker,
    UnknownConfiguration,
    UnknownUser,
    UnsupportedEngineType,
    UnknownEngineType,
)


class ConfigurationRevision(BaseModel):
    def __init__(self, configuration_id, revision_id, description, data=None):
        self.configuration_id = configuration_id
        self.created = unix_time()
        self.description = description
        self.is_invalid = False
        self.revision_id = revision_id

        if data is None:
            self.data = base64.b64encode(
                DEFAULT_CONFIGURATION_DATA.encode("UTF-8")
            ).decode("utf-8")
        else:
            self.data = data

    def has_ldap_auth(self):
        try:
            xml = base64.b64decode(self.data)
            dct = xmltodict.parse(xml, dict_constructor=dict)
            return (
                "cachedLDAPAuthorizationMap"
                in dct["broker"]["plugins"]["authorizationPlugin"]["map"]
            )
        except Exception:
            # There are many configurations to enable LDAP
            # We're only checking for one here
            # If anything fails, lets assume it's not LDAP
            return False

    def to_json(self, full=True):
        resp = {
            "created": self.created,
            "description": self.description,
            "revision": int(self.revision_id),
        }
        if full:
            resp["configurationId"] = self.configuration_id
            resp["data"] = self.data
        return resp


class Configuration(BaseModel):
    def __init__(self, account_id, region, name, engine_type, engine_version):
        self.id = f"c-{mock_random.get_random_hex(6)}"
        self.arn = f"arn:aws:mq:{region}:{account_id}:configuration:{self.id}"
        self.created = unix_time()

        self.name = name
        self.engine_type = engine_type
        self.engine_version = engine_version

        self.revisions = dict()
        default_desc = (
            f"Auto-generated default for {self.name} on {engine_type} {engine_version}"
        )
        latest_revision = ConfigurationRevision(
            configuration_id=self.id, revision_id="1", description=default_desc
        )
        self.revisions[latest_revision.revision_id] = latest_revision

        self.authentication_strategy = (
            "ldap" if latest_revision.has_ldap_auth() else "simple"
        )

    def update(self, data, description):
        max_revision_id, _ = sorted(self.revisions.items())[-1]
        next_revision_id = str(int(max_revision_id) + 1)
        latest_revision = ConfigurationRevision(
            configuration_id=self.id,
            revision_id=next_revision_id,
            description=description,
            data=data,
        )
        self.revisions[next_revision_id] = latest_revision

        self.authentication_strategy = (
            "ldap" if latest_revision.has_ldap_auth() else "simple"
        )

    def get_revision(self, revision_id):
        return self.revisions[revision_id]

    def to_json(self):
        _, latest_revision = sorted(self.revisions.items())[-1]
        return {
            "arn": self.arn,
            "authenticationStrategy": self.authentication_strategy,
            "created": self.created,
            "engineType": self.engine_type,
            "engineVersion": self.engine_version,
            "id": self.id,
            "name": self.name,
            "latestRevision": latest_revision.to_json(full=False),
        }


class User(BaseModel):
    def __init__(self, broker_id, username, console_access=None, groups=None):
        self.broker_id = broker_id
        self.username = username
        self.console_access = console_access or False
        self.groups = groups or []

    def update(self, console_access, groups):
        if console_access is not None:
            self.console_access = console_access
        if groups:
            self.groups = groups

    def summary(self):
        return {"username": self.username}

    def to_json(self):
        return {
            "brokerId": self.broker_id,
            "username": self.username,
            "consoleAccess": self.console_access,
            "groups": self.groups,
        }


class Broker(BaseModel):
    def __init__(
        self,
        name,
        account_id,
        region,
        authentication_strategy,
        auto_minor_version_upgrade,
        configuration,
        deployment_mode,
        encryption_options,
        engine_type,
        engine_version,
        host_instance_type,
        ldap_server_metadata,
        logs,
        maintenance_window_start_time,
        publicly_accessible,
        security_groups,
        storage_type,
        subnet_ids,
        users,
    ):
        self.name = name
        self.id = mock_random.get_random_hex(6)
        self.arn = f"arn:aws:mq:{region}:{account_id}:broker:{self.id}"
        self.state = "RUNNING"
        self.created = unix_time()

        self.authentication_strategy = authentication_strategy
        self.auto_minor_version_upgrade = auto_minor_version_upgrade
        self.deployment_mode = deployment_mode
        self.encryption_options = encryption_options
        if not self.encryption_options:
            self.encryption_options = {"useAwsOwnedKey": True}
        self.engine_type = engine_type
        self.engine_version = engine_version
        self.host_instance_type = host_instance_type
        self.ldap_server_metadata = ldap_server_metadata
        self.logs = logs
        if "general" not in self.logs:
            self.logs["general"] = False
        if "audit" not in self.logs:
            if self.engine_type.upper() == "ACTIVEMQ":
                self.logs["audit"] = False
        self.maintenance_window_start_time = maintenance_window_start_time
        if not self.maintenance_window_start_time:
            self.maintenance_window_start_time = {
                "dayOfWeek": "Sunday",
                "timeOfDay": "00:00",
                "timeZone": "UTC",
            }
        self.publicly_accessible = publicly_accessible
        self.security_groups = security_groups
        self.storage_type = storage_type
        self.subnet_ids = subnet_ids
        if not self.subnet_ids:
            if self.deployment_mode == "CLUSTER_MULTI_AZ":
                self.subnet_ids = [
                    "default-az1",
                    "default-az2",
                    "default-az3",
                    "default-az4",
                ]
            elif self.deployment_mode == "ACTIVE_STANDBY_MULTI_AZ":
                self.subnet_ids = ["active-subnet", "standby-subnet"]
            else:
                self.subnet_ids = ["default-subnet"]

        self.users = dict()
        for user in users:
            self.create_user(
                username=user["username"],
                groups=user.get("groups", []),
                console_access=user.get("consoleAccess", False),
            )

        if self.engine_type.upper() == "RABBITMQ":
            self.configurations = None
        else:
            current_config = configuration or {
                "id": f"c-{mock_random.get_random_hex(6)}",
                "revision": 1,
            }
            self.configurations = {
                "current": current_config,
                "history": [],
            }
        if self.engine_type.upper() == "RABBITMQ":
            console_url = f"https://0000.mq.{region}.amazonaws.com"
            endpoints = ["amqps://mockmq:5671"]
        else:
            console_url = f"https://0000.mq.{region}.amazonaws.com:8162"
            endpoints = [
                "ssl://mockmq:61617",
                "amqp+ssl://mockmq:5671",
                "stomp+ssl://mockmq:61614",
                "mqtt+ssl://mockmq:8883",
                "wss://mockmq:61619",
            ]
        self.instances = [
            {
                "consoleURL": console_url,
                "endpoints": endpoints,
                "ipAddress": "192.168.0.1",
            }
        ]

        if deployment_mode == "ACTIVE_STANDBY_MULTI_AZ":
            self.instances.append(
                {
                    "consoleURL": console_url,
                    "endpoints": endpoints,
                    "ipAddress": "192.168.0.2",
                }
            )

    def update(
        self,
        authentication_strategy,
        auto_minor_version_upgrade,
        configuration,
        engine_version,
        host_instance_type,
        ldap_server_metadata,
        logs,
        maintenance_window_start_time,
        security_groups,
    ):
        if authentication_strategy:
            self.authentication_strategy = authentication_strategy
        if auto_minor_version_upgrade is not None:
            self.auto_minor_version_upgrade = auto_minor_version_upgrade
        if configuration:
            self.configurations["history"].append(self.configurations["current"])
            self.configurations["current"] = configuration
        if engine_version:
            self.engine_version = engine_version
        if host_instance_type:
            self.host_instance_type = host_instance_type
        if ldap_server_metadata:
            self.ldap_server_metadata = ldap_server_metadata
        if logs:
            self.logs = logs
        if maintenance_window_start_time:
            self.maintenance_window_start_time = maintenance_window_start_time
        if security_groups:
            self.security_groups = security_groups

    def reboot(self):
        pass

    def create_user(self, username, console_access, groups):
        user = User(self.id, username, console_access, groups)
        self.users[username] = user

    def update_user(self, username, console_access, groups):
        user = self.get_user(username)
        user.update(console_access, groups)

    def get_user(self, username):
        if username not in self.users:
            raise UnknownUser(username)
        return self.users[username]

    def delete_user(self, username):
        self.users.pop(username, None)

    def list_users(self):
        return self.users.values()

    def summary(self):
        return {
            "brokerArn": self.arn,
            "brokerId": self.id,
            "brokerName": self.name,
            "brokerState": self.state,
            "created": self.created,
            "deploymentMode": self.deployment_mode,
            "engineType": self.engine_type,
            "hostInstanceType": self.host_instance_type,
        }

    def to_json(self):
        return {
            "brokerId": self.id,
            "brokerArn": self.arn,
            "brokerName": self.name,
            "brokerState": self.state,
            "brokerInstances": self.instances,
            "created": self.created,
            "configurations": self.configurations,
            "authenticationStrategy": self.authentication_strategy,
            "autoMinorVersionUpgrade": self.auto_minor_version_upgrade,
            "deploymentMode": self.deployment_mode,
            "encryptionOptions": self.encryption_options,
            "engineType": self.engine_type,
            "engineVersion": self.engine_version,
            "hostInstanceType": self.host_instance_type,
            "ldapServerMetadata": self.ldap_server_metadata,
            "logs": self.logs,
            "maintenanceWindowStartTime": self.maintenance_window_start_time,
            "publiclyAccessible": self.publicly_accessible,
            "securityGroups": self.security_groups,
            "storageType": self.storage_type,
            "subnetIds": self.subnet_ids,
            "users": [u.summary() for u in self.users.values()],
        }


class MQBackend(BaseBackend):
    """
    No EC2 integration exists yet - subnet ID's and security group values are not validated. Default values may not exist.
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.brokers = dict()
        self.configs = dict()
        self.tagger = TaggingService()

    def create_broker(
        self,
        authentication_strategy,
        auto_minor_version_upgrade,
        broker_name,
        configuration,
        deployment_mode,
        encryption_options,
        engine_type,
        engine_version,
        host_instance_type,
        ldap_server_metadata,
        logs,
        maintenance_window_start_time,
        publicly_accessible,
        security_groups,
        storage_type,
        subnet_ids,
        tags,
        users,
    ):
        broker = Broker(
            name=broker_name,
            account_id=self.account_id,
            region=self.region_name,
            authentication_strategy=authentication_strategy,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
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
            users=users,
        )
        self.brokers[broker.id] = broker
        self.create_tags(broker.arn, tags)
        return broker.arn, broker.id

    def delete_broker(self, broker_id):
        del self.brokers[broker_id]

    def describe_broker(self, broker_id):
        if broker_id not in self.brokers:
            raise UnknownBroker(broker_id)
        return self.brokers[broker_id]

    def reboot_broker(self, broker_id):
        self.brokers[broker_id].reboot()

    def list_brokers(self):
        """
        Pagination is not yet implemented
        """
        return self.brokers.values()

    def create_user(self, broker_id, username, console_access, groups):
        broker = self.describe_broker(broker_id)
        broker.create_user(username, console_access, groups)

    def update_user(self, broker_id, console_access, groups, username):
        broker = self.describe_broker(broker_id)
        broker.update_user(username, console_access, groups)

    def describe_user(self, broker_id, username):
        broker = self.describe_broker(broker_id)
        return broker.get_user(username)

    def delete_user(self, broker_id, username):
        broker = self.describe_broker(broker_id)
        broker.delete_user(username)

    def list_users(self, broker_id):
        broker = self.describe_broker(broker_id)
        return broker.list_users()

    def create_configuration(self, name, engine_type, engine_version, tags):
        if engine_type.upper() == "RABBITMQ":
            raise UnsupportedEngineType(engine_type)
        if engine_type.upper() != "ACTIVEMQ":
            raise UnknownEngineType(engine_type)
        config = Configuration(
            account_id=self.account_id,
            region=self.region_name,
            name=name,
            engine_type=engine_type,
            engine_version=engine_version,
        )
        self.configs[config.id] = config
        self.tagger.tag_resource(
            config.arn, self.tagger.convert_dict_to_tags_input(tags)
        )
        return config

    def update_configuration(self, config_id, data, description):
        """
        No validation occurs on the provided XML. The authenticationStrategy may be changed depending on the provided configuration.
        """
        config = self.configs[config_id]
        config.update(data, description)
        return config

    def describe_configuration(self, config_id):
        if config_id not in self.configs:
            raise UnknownConfiguration(config_id)
        return self.configs[config_id]

    def describe_configuration_revision(self, config_id, revision_id):
        config = self.configs[config_id]
        return config.get_revision(revision_id)

    def list_configurations(self):
        """
        Pagination has not yet been implemented.
        """
        return self.configs.values()

    def create_tags(self, resource_arn, tags):
        self.tagger.tag_resource(
            resource_arn, self.tagger.convert_dict_to_tags_input(tags)
        )

    def list_tags(self, arn):
        return self.tagger.get_tag_dict_for_resource(arn)

    def delete_tags(self, resource_arn, tag_keys):
        if not isinstance(tag_keys, list):
            tag_keys = [tag_keys]
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def update_broker(
        self,
        authentication_strategy,
        auto_minor_version_upgrade,
        broker_id,
        configuration,
        engine_version,
        host_instance_type,
        ldap_server_metadata,
        logs,
        maintenance_window_start_time,
        security_groups,
    ):
        broker = self.describe_broker(broker_id)
        broker.update(
            authentication_strategy=authentication_strategy,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            configuration=configuration,
            engine_version=engine_version,
            host_instance_type=host_instance_type,
            ldap_server_metadata=ldap_server_metadata,
            logs=logs,
            maintenance_window_start_time=maintenance_window_start_time,
            security_groups=security_groups,
        )


mq_backends = BackendDict(MQBackend, "mq")
