from moto.core.responses import BaseResponse

from .exceptions import (
    InvalidParameterCombinationException,
    InvalidParameterValueException,
    PasswordTooShort,
)
from .models import ElastiCacheBackend, elasticache_backends
from .utils import VALID_AUTH_MODE_KEYS, VALID_ENGINE_TYPES, AuthenticationTypes


class ElastiCacheResponse(BaseResponse):
    """Handler for ElastiCache requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="elasticache")

    @property
    def elasticache_backend(self) -> ElastiCacheBackend:
        """Return backend instance specific for this region."""
        return elasticache_backends[self.current_account][self.region]

    def create_user(self) -> str:
        params = self._get_params()
        user_id = params.get("UserId")
        user_name = params.get("UserName")
        engine = params.get("Engine", "").lower()
        passwords = params.get("Passwords", [])
        no_password_required = self._get_bool_param("NoPasswordRequired")
        authentication_mode = params.get("AuthenticationMode")
        authentication_type = "null"

        if no_password_required is not None:
            authentication_type = (
                AuthenticationTypes.NOPASSWORD.value
                if no_password_required
                else AuthenticationTypes.PASSWORD.value
            )

        if passwords:
            authentication_type = AuthenticationTypes.PASSWORD.value

        if engine not in VALID_ENGINE_TYPES:
            raise InvalidParameterValueException(
                f'Unknown parameter for Engine: "{engine}", must be one of: {", ".join(VALID_ENGINE_TYPES)}'
            )

        if authentication_mode:
            for key in authentication_mode.keys():
                if key not in VALID_AUTH_MODE_KEYS:
                    raise InvalidParameterValueException(
                        f'Unknown parameter in AuthenticationMode: "{key}", must be one of: {", ".join(VALID_AUTH_MODE_KEYS)}'
                    )

            authentication_type = authentication_mode.get("Type")
            authentication_passwords = authentication_mode.get("Passwords", [])

            if passwords and authentication_passwords:
                raise InvalidParameterCombinationException(
                    "Passwords provided via multiple arguments. Use only one argument"
                )

            # if passwords is empty, then we can use the authentication_passwords
            passwords = passwords if passwords else authentication_passwords

        if any([len(p) < 16 for p in passwords]):
            raise PasswordTooShort

        access_string = params.get("AccessString")
        user = self.elasticache_backend.create_user(
            user_id=user_id,  # type: ignore[arg-type]
            user_name=user_name,  # type: ignore[arg-type]
            engine=engine,  # type: ignore[arg-type]
            passwords=passwords,
            access_string=access_string,  # type: ignore[arg-type]
            no_password_required=no_password_required,
            authentication_type=authentication_type,
        )
        template = self.response_template(CREATE_USER_TEMPLATE)
        return template.render(user=user)

    def delete_user(self) -> str:
        params = self._get_params()
        user_id = params.get("UserId")
        user = self.elasticache_backend.delete_user(user_id=user_id)  # type: ignore[arg-type]
        template = self.response_template(DELETE_USER_TEMPLATE)
        return template.render(user=user)

    def describe_users(self) -> str:
        params = self._get_params()
        user_id = params.get("UserId")
        users = self.elasticache_backend.describe_users(user_id=user_id)
        template = self.response_template(DESCRIBE_USERS_TEMPLATE)
        return template.render(users=users)

    def create_cache_cluster(self) -> str:
        cache_cluster_id = self._get_param("CacheClusterId")
        replication_group_id = self._get_param("ReplicationGroupId")
        az_mode = self._get_param("AZMode")
        preferred_availability_zone = self._get_param("PreferredAvailabilityZone")
        preferred_availability_zones = self._get_param("PreferredAvailabilityZones")
        num_cache_nodes = self._get_int_param("NumCacheNodes")
        cache_node_type = self._get_param("CacheNodeType")
        engine = self._get_param("Engine")
        engine_version = self._get_param("EngineVersion")
        cache_parameter_group_name = self._get_param("CacheParameterGroupName")
        cache_subnet_group_name = self._get_param("CacheSubnetGroupName")
        cache_security_group_names = self._get_param("CacheSecurityGroupNames")
        security_group_ids = self._get_param("SecurityGroupIds")
        tags = (self._get_multi_param_dict("Tags") or {}).get("Tag", [])
        snapshot_arns = self._get_param("SnapshotArns")
        snapshot_name = self._get_param("SnapshotName")
        preferred_maintenance_window = self._get_param("PreferredMaintenanceWindow")
        port = self._get_param("Port")
        notification_topic_arn = self._get_param("NotificationTopicArn")
        auto_minor_version_upgrade = self._get_bool_param("AutoMinorVersionUpgrade")
        snapshot_retention_limit = self._get_int_param("SnapshotRetentionLimit")
        snapshot_window = self._get_param("SnapshotWindow")
        auth_token = self._get_param("AuthToken")
        outpost_mode = self._get_param("OutpostMode")
        preferred_outpost_arn = self._get_param("PreferredOutpostArn")
        preferred_outpost_arns = self._get_param("PreferredOutpostArns")
        log_delivery_configurations = self._get_param("LogDeliveryConfigurations")
        transit_encryption_enabled = self._get_bool_param("TransitEncryptionEnabled")
        network_type = self._get_param("NetworkType")
        ip_discovery = self._get_param("IpDiscovery")
        # Define the following attributes as they're included in the response even during creation of a cache cluster
        cache_node_ids_to_remove = self._get_param("CacheNodeIdsToRemove", [])
        cache_node_ids_to_reboot = self._get_param("CacheNodeIdsToReboot", [])
        cache_cluster = self.elasticache_backend.create_cache_cluster(
            cache_cluster_id=cache_cluster_id,
            replication_group_id=replication_group_id,
            az_mode=az_mode,
            preferred_availability_zone=preferred_availability_zone,
            preferred_availability_zones=preferred_availability_zones,
            num_cache_nodes=num_cache_nodes,
            cache_node_type=cache_node_type,
            engine=engine,
            engine_version=engine_version,
            cache_parameter_group_name=cache_parameter_group_name,
            cache_subnet_group_name=cache_subnet_group_name,
            cache_security_group_names=cache_security_group_names,
            security_group_ids=security_group_ids,
            tags=tags,
            snapshot_arns=snapshot_arns,
            snapshot_name=snapshot_name,
            preferred_maintenance_window=preferred_maintenance_window,
            port=port,
            notification_topic_arn=notification_topic_arn,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            snapshot_retention_limit=snapshot_retention_limit,
            snapshot_window=snapshot_window,
            auth_token=auth_token,
            outpost_mode=outpost_mode,
            preferred_outpost_arn=preferred_outpost_arn,
            preferred_outpost_arns=preferred_outpost_arns,
            log_delivery_configurations=log_delivery_configurations,
            transit_encryption_enabled=transit_encryption_enabled,
            network_type=network_type,
            ip_discovery=ip_discovery,
            cache_node_ids_to_remove=cache_node_ids_to_remove,
            cache_node_ids_to_reboot=cache_node_ids_to_reboot,
        )
        template = self.response_template(CREATE_CACHE_CLUSTER_TEMPLATE)
        return template.render(cache_cluster=cache_cluster)

    def describe_cache_clusters(self) -> str:
        cache_cluster_id = self._get_param("CacheClusterId")
        max_records = self._get_int_param("MaxRecords")
        marker = self._get_param("Marker")

        cache_clusters, marker = self.elasticache_backend.describe_cache_clusters(
            cache_cluster_id=cache_cluster_id,
            marker=marker,
            max_records=max_records,
        )
        template = self.response_template(DESCRIBE_CACHE_CLUSTERS_TEMPLATE)
        return template.render(marker=marker, cache_clusters=cache_clusters)

    def delete_cache_cluster(self) -> str:
        cache_cluster_id = self._get_param("CacheClusterId")
        cache_cluster = self.elasticache_backend.delete_cache_cluster(
            cache_cluster_id=cache_cluster_id,
        )
        template = self.response_template(DELETE_CACHE_CLUSTER_TEMPLATE)
        return template.render(cache_cluster=cache_cluster)

    def list_tags_for_resource(self) -> str:
        arn = self._get_param("ResourceName")
        template = self.response_template(LIST_TAGS_FOR_RESOURCE_TEMPLATE)
        tags = self.elasticache_backend.list_tags_for_resource(arn)
        return template.render(tags=tags)

    def create_cache_subnet_group(self) -> str:
        cache_subnet_group_name = self._get_param("CacheSubnetGroupName")
        cache_subnet_group_description = self._get_param("CacheSubnetGroupDescription")
        subnet_ids = self._get_multi_param_dict("SubnetIds").get("SubnetIdentifier", [])
        tags = (self._get_multi_param_dict("Tags") or {}).get("Tag", [])
        cache_subnet_group = self.elasticache_backend.create_cache_subnet_group(
            cache_subnet_group_name=cache_subnet_group_name,
            cache_subnet_group_description=cache_subnet_group_description,
            subnet_ids=subnet_ids,
            tags=tags,
        )
        template = self.response_template(CREATE_CACHE_SUBNET_GROUP_TEMPLATE)
        return template.render(cache_subnet_group=cache_subnet_group)

    def describe_cache_subnet_groups(self) -> str:
        cache_subnet_group_name = self._get_param("CacheSubnetGroupName")
        max_records = self._get_param("MaxRecords")
        marker = self._get_param("Marker")
        cache_subnet_groups, marker = (
            self.elasticache_backend.describe_cache_subnet_groups(
                cache_subnet_group_name=cache_subnet_group_name,
                marker=marker,
                max_records=max_records,
            )
        )
        template = self.response_template(DESCRIBE_CACHE_SUBNET_GROUPS_TEMPLATE)
        return template.render(marker=marker, cache_subnet_groups=cache_subnet_groups)

    def create_replication_group(self) -> str:
        replication_group_id = self._get_param("ReplicationGroupId")
        replication_group_description = self._get_param("ReplicationGroupDescription")
        global_replication_group_id = self._get_param("GlobalReplicationGroupId")
        primary_cluster_id = self._get_param("PrimaryClusterId")
        automatic_failover_enabled = self._get_bool_param("AutomaticFailoverEnabled")
        multi_az_enabled = self._get_bool_param("MultiAZEnabled")
        num_cache_clusters = self._get_int_param("NumCacheClusters")
        preferred_cache_cluster_azs = self._get_param("PreferredCacheClusterAZs")
        num_node_groups = self._get_int_param("NumNodeGroups")
        replicas_per_node_group = self._get_int_param("ReplicasPerNodeGroup")
        node_group_configuration = (
            self._get_multi_param_dict("NodeGroupConfiguration").get(
                "NodeGroupConfiguration", []
            )
            if self._get_multi_param_dict("NodeGroupConfiguration")
            else []
        )
        cache_node_type = self._get_param("CacheNodeType")
        engine = self._get_param("Engine")
        engine_version = self._get_param("EngineVersion")
        cache_parameter_group_name = self._get_param("CacheParameterGroupName")
        cache_subnet_group_name = self._get_param("CacheSubnetGroupName")
        cache_security_group_names = self._get_param("CacheSecurityGroupNames")
        security_group_ids = self._get_param("SecurityGroupIds")
        tags = (self._get_multi_param_dict("Tags") or {}).get("Tag", [])
        snapshot_arns = self._get_param("SnapshotArns")
        snapshot_name = self._get_param("SnapshotName")
        preferred_maintenance_window = self._get_param("PreferredMaintenanceWindow")
        port = self._get_param("Port")
        notification_topic_arn = self._get_param("NotificationTopicArn")
        auto_minor_version_upgrade = self._get_param("AutoMinorVersionUpgrade")
        snapshot_retention_limit = self._get_int_param("SnapshotRetentionLimit")
        snapshot_window = self._get_param("SnapshotWindow")
        auth_token = self._get_param("AuthToken")
        transit_encryption_enabled = self._get_bool_param("TransitEncryptionEnabled")
        at_rest_encryption_enabled = self._get_bool_param("AtRestEncryptionEnabled")
        kms_key_id = self._get_param("KmsKeyId")
        user_group_ids = self._get_param("UserGroupIds")
        log_delivery_configurations = self._get_param("LogDeliveryConfigurations")
        data_tiering_enabled = self._get_param("DataTieringEnabled")
        network_type = self._get_param("NetworkType")
        ip_discovery = self._get_param("IpDiscovery")
        transit_encryption_mode = self._get_param("TransitEncryptionMode")
        cluster_mode = self._get_param("ClusterMode")
        serverless_cache_snapshot_name = self._get_param("ServerlessCacheSnapshotName")
        replication_group = self.elasticache_backend.create_replication_group(
            replication_group_id=replication_group_id,
            replication_group_description=replication_group_description,
            global_replication_group_id=global_replication_group_id,
            primary_cluster_id=primary_cluster_id,
            automatic_failover_enabled=automatic_failover_enabled,
            multi_az_enabled=multi_az_enabled,
            num_cache_clusters=num_cache_clusters,
            preferred_cache_cluster_azs=preferred_cache_cluster_azs,
            num_node_groups=num_node_groups,
            replicas_per_node_group=replicas_per_node_group,
            node_group_configuration=node_group_configuration,
            cache_node_type=cache_node_type,
            engine=engine,
            engine_version=engine_version,
            cache_parameter_group_name=cache_parameter_group_name,
            cache_subnet_group_name=cache_subnet_group_name,
            cache_security_group_names=cache_security_group_names,
            security_group_ids=security_group_ids,
            tags=tags,
            snapshot_arns=snapshot_arns,
            snapshot_name=snapshot_name,
            preferred_maintenance_window=preferred_maintenance_window,
            port=port,
            notification_topic_arn=notification_topic_arn,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            snapshot_retention_limit=snapshot_retention_limit,
            snapshot_window=snapshot_window,
            auth_token=auth_token,
            transit_encryption_enabled=transit_encryption_enabled,
            at_rest_encryption_enabled=at_rest_encryption_enabled,
            kms_key_id=kms_key_id,
            user_group_ids=user_group_ids,
            log_delivery_configurations=log_delivery_configurations,
            data_tiering_enabled=data_tiering_enabled,
            network_type=network_type,
            ip_discovery=ip_discovery,
            transit_encryption_mode=transit_encryption_mode,
            cluster_mode=cluster_mode,
            serverless_cache_snapshot_name=serverless_cache_snapshot_name,
        )
        template = self.response_template(CREATE_REPLICATION_GROUP_TEMPLATE)
        return template.render(replication_group=replication_group)

    def describe_replication_groups(self) -> str:
        replication_group_id = self._get_param("ReplicationGroupId")
        max_records = self._get_param("MaxRecords")
        marker = self._get_param("Marker")
        replication_groups, marker = (
            self.elasticache_backend.describe_replication_groups(
                replication_group_id=replication_group_id,
                marker=marker,
                max_records=max_records,
            )
        )
        template = self.response_template(DESCRIBE_REPLICATION_GROUPS_TEMPLATE)
        return template.render(marker=marker, replication_groups=replication_groups)


USER_TEMPLATE = """<UserId>{{ user.id }}</UserId>
    <UserName>{{ user.name }}</UserName>
    <Status>{{ user.status }}</Status>
    <Engine>{{ user.engine }}</Engine>
    <MinimumEngineVersion>{{ user.minimum_engine_version }}</MinimumEngineVersion>
    <AccessString>{{ user.access_string }}</AccessString>
    <UserGroupIds>
{% for usergroupid in user.usergroupids %}
      <member>{{ usergroupid }}</member>
{% endfor %}
    </UserGroupIds>
    <Authentication>
      {% if user.no_password_required %}
      <Type>no-password</Type>
      {% else %}
      <Type>{{ user.authentication_type }}</Type>
      {% endif %}
      {% if user.passwords %}
      <PasswordCount>{{ user.passwords|length }}</PasswordCount>
      {% endif %}
    </Authentication>
    <ARN>{{ user.arn }}</ARN>"""

CREATE_USER_TEMPLATE = (
    """<CreateUserResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
          <ResponseMetadata>
            <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
          </ResponseMetadata>
          <CreateUserResult>
            """
    + USER_TEMPLATE
    + """
  </CreateUserResult>
</CreateUserResponse>"""
)

DELETE_USER_TEMPLATE = (
    """<DeleteUserResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
          <ResponseMetadata>
            <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
          </ResponseMetadata>
          <DeleteUserResult>
            """
    + USER_TEMPLATE
    + """
  </DeleteUserResult>
</DeleteUserResponse>"""
)

DESCRIBE_USERS_TEMPLATE = (
    """<DescribeUsersResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
          <ResponseMetadata>
            <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
          </ResponseMetadata>
          <DescribeUsersResult>
            <Users>
        {% for user in users %}
              <member>
                """
    + USER_TEMPLATE
    + """
      </member>
{% endfor %}
    </Users>
    <Marker></Marker>
  </DescribeUsersResult>
</DescribeUsersResponse>"""
)

CREATE_CACHE_CLUSTER_TEMPLATE = """<CreateCacheClusterResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <CreateCacheClusterResult>
    <CacheCluster>
  <CacheClusterId>{{ cache_cluster.cache_cluster_id }}</CacheClusterId>
  <ConfigurationEndpoint>
    <Address>example.cache.amazonaws.com</Address>
    <Port>{{ cache_cluster.port }}</Port>
  </ConfigurationEndpoint>
  <ClientDownloadLandingPage></ClientDownloadLandingPage>
  <CacheNodeType>{{ cache_cluster.cache_node_type }}</CacheNodeType>
  <Engine>{{ cache_cluster.engine }}</Engine>
  <EngineVersion>{{ cache_cluster.engine_version }}</EngineVersion>
  <CacheClusterStatus>available</CacheClusterStatus>
  <NumCacheNodes>{{ cache_cluster.num_cache_nodes }}</NumCacheNodes>
  <PreferredAvailabilityZone>{{ cache_cluster.preferred_availability_zone }}</PreferredAvailabilityZone>
  <PreferredOutpostArn>{{ cache_cluster.preferred_outpost_arn }}</PreferredOutpostArn>
  <CacheClusterCreateTime>{{ cache_cluster.cache_cluster_create_time }}</CacheClusterCreateTime>
  <PreferredMaintenanceWindow>{{ cache_cluster.preferred_maintenance_window }}</PreferredMaintenanceWindow>
  {% if cache_cluster.cache_node_ids_to_remove != [] %}
  <PendingModifiedValues>
    <NumCacheNodes>{{ cache_cluster.num_cache_nodes }}</NumCacheNodes>
    {% for cache_node_id_to_remove in cache_cluster.cache_node_ids_to_remove %}
    <CacheNodeIdsToRemove>{{ cache_node_id_to_remove }}</CacheNodeIdsToRemove>
    {% endfor %}
    <EngineVersion>{{ cache_cluster.engine_version }}</EngineVersion>
    <CacheNodeType>{{ cache_cluster.cache_node_type }}</CacheNodeType>
    <AuthTokenStatus>SETTING</AuthTokenStatus>
    <LogDeliveryConfigurations>
    {% for log_delivery_configuration in cache_cluster.log_delivery_configurations %}
      <LogType>{{ log_delivery_configuration.LogType }}</LogType>
      <DestinationType>{{ log_delivery_configuration.DestinationType }}</DestinationType>
      <DestinationDetails>
        <CloudWatchLogsDetails>
          <LogGroup>{{ log_delivery_configuration.LogGroup }}</LogGroup>
        </CloudWatchLogsDetails>
        <KinesisFirehoseDetails>
          <DeliveryStream>{{ log_delivery_configuration.DeliveryStream }}</DeliveryStream>
        </KinesisFirehoseDetails>
      </DestinationDetails>
      <LogFormat>{{ log_delivery_configuration.LogFormat }}</LogFormat>
      {% endfor %}
    </LogDeliveryConfigurations>
    <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
    <TransitEncryptionMode>preferred</TransitEncryptionMode>
  </PendingModifiedValues>
  {% endif %}
  <NotificationConfiguration>
    <TopicArn>{{ cache_cluster.notification_topic_arn }}</TopicArn>
    <TopicStatus>active</TopicStatus>
  </NotificationConfiguration>
  <CacheSecurityGroups>
  {% for cache_security_group_name in cache_cluster.cache_security_group_names %}
    <CacheSecurityGroupName>{{ cache_security_group_name }}</CacheSecurityGroupName>
    {% endfor %}
    <Status>active</Status>
  </CacheSecurityGroups>
  <CacheParameterGroup>
    <CacheParameterGroupName>{{ cache_cluster.cache_parameter_group_name }}</CacheParameterGroupName>
    <ParameterApplyStatus>active</ParameterApplyStatus>
    {% for cache_node_id_to_reboot in cache_cluster.cache_node_ids_to_reboot %}
    <CacheNodeIdsToReboot>
    {{ cache_node_id_to_reboot }}
    </CacheNodeIdsToReboot>
    {% endfor %}
  </CacheParameterGroup>
  <CacheSubnetGroupName>{{ cache_cluster.cache_subnet_group_name }}</CacheSubnetGroupName>
  <CacheNodes>
    <CacheNodeId>{{ cache_cluster.cache_node_id }}</CacheNodeId>
    <CacheNodeStatus>{{ cache_cluster.cache_node_status }}</CacheNodeStatus>
    <CacheNodeCreateTime>{{ cache_cluster.cache_cluster_create_time }}</CacheNodeCreateTime>
    <Endpoint>
      <Address>{{ cache_cluster.address }}</Address>
      <Port>{{ cache_cluster.port }}</Port>
    </Endpoint>
    <ParameterGroupStatus>active</ParameterGroupStatus>
    <SourceCacheNodeId>{{ cache_cluster.cache_node_id }}</SourceCacheNodeId>
    <CustomerAvailabilityZone>{{ cache_cluster.preferred_availability_zone }}</CustomerAvailabilityZone>
    <CustomerOutpostArn>{{ cache_cluster.preferred_output_arn }}</CustomerOutpostArn>
  </CacheNodes>
  <AutoMinorVersionUpgrade>{{ cache_cluster.auto_minor_version_upgrade|lower }}</AutoMinorVersionUpgrade>
  <SecurityGroups>
  {% for security_group_id in cache_cluster.security_group_ids %}
    <SecurityGroupId>{{ security_group_id }}</SecurityGroupId>
    <Status>active</Status>
    {% endfor %}
  </SecurityGroups>
  {% if cache_cluster.engine == "redis" %}
  <ReplicationGroupId>{{ cache_cluster.replication_group_id }}</ReplicationGroupId>
  <SnapshotRetentionLimit>{{ cache_cluster.snapshot_retention_limit }}</SnapshotRetentionLimit>
  <SnapshotWindow>{{ cache_cluster.snapshot_window }}</SnapshotWindow>
  {% endif %}
  <AuthTokenEnabled>true</AuthTokenEnabled>
  <AuthTokenLastModifiedDate>{{ cache_cluster.cache_cluster_create_time }}</AuthTokenLastModifiedDate>
  <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
  <AtRestEncryptionEnabled>true</AtRestEncryptionEnabled>
  <ARN>{{ cache_cluster.arn }}</ARN>
  <ReplicationGroupLogDeliveryEnabled>true</ReplicationGroupLogDeliveryEnabled>
  <LogDeliveryConfigurations>
  {% for log_delivery_configuration in cache_cluster.log_delivery_configurations %}
      <LogType>{{ log_delivery_configuration.LogType }}</LogType>
      <DestinationType>{{ log_delivery_configuration.DestinationType }}</DestinationType>
      <DestinationDetails>
        <CloudWatchLogsDetails>
          <LogGroup>{{ log_delivery_configuration.LogGroup }}</LogGroup>
        </CloudWatchLogsDetails>
        <KinesisFirehoseDetails>
          <DeliveryStream>{{ log_delivery_configuration.DeliveryStream }}</DeliveryStream>
        </KinesisFirehoseDetails>
      </DestinationDetails>
      <LogFormat>{{ log_delivery_configuration.LogFormat }}</LogFormat>
      <Status>active</Status>
      <Message></Message>
  {% endfor %}
  </LogDeliveryConfigurations>
  <NetworkType>{{ cache_cluster.network_type }}</NetworkType>
  <IpDiscovery>{{ cache_cluster.ip_discovery }}</IpDiscovery>
  <TransitEncryptionMode>preferred</TransitEncryptionMode>
</CacheCluster>
  </CreateCacheClusterResult>
</CreateCacheClusterResponse>"""

DESCRIBE_CACHE_CLUSTERS_TEMPLATE = """<DescribeCacheClustersResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <DescribeCacheClustersResult>
    {% if marker %}<Marker>{{ marker }}</Marker>{% endif %}
    <CacheClusters>
{% for cache_cluster in cache_clusters %}
      <member>
        <CacheClusterId>{{ cache_cluster.cache_cluster_id }}</CacheClusterId>
        <ConfigurationEndpoint>{{ cache_cluster.configuration_endpoint }}</ConfigurationEndpoint>
        <ClientDownloadLandingPage>{{ cache_cluster.client_download_landing_page }}</ClientDownloadLandingPage>
        <CacheNodeType>{{ cache_cluster.cache_node_type }}</CacheNodeType>
        <Engine>{{ cache_cluster.engine }}</Engine>
        <EngineVersion>{{ cache_cluster.engine_version }}</EngineVersion>
        <CacheClusterStatus>{{ cache_cluster.cache_cluster_status }}</CacheClusterStatus>
        <NumCacheNodes>{{ cache_cluster.num_cache_nodes }}</NumCacheNodes>
        <PreferredAvailabilityZone>{{ cache_cluster.preferred_availability_zone }}</PreferredAvailabilityZone>
        <PreferredOutpostArn>{{ cache_cluster.preferred_outpost_arn }}</PreferredOutpostArn>
        <CacheClusterCreateTime>{{ cache_cluster.cache_cluster_create_time }}</CacheClusterCreateTime>
        <PreferredMaintenanceWindow>{{ cache_cluster.preferred_maintenance_window }}</PreferredMaintenanceWindow>
        <PendingModifiedValues>{{ cache_cluster.pending_modified_values }}</PendingModifiedValues>
        <NotificationConfiguration>{{ cache_cluster.notification_configuration }}</NotificationConfiguration>
        <CacheSecurityGroups>
{% for cache_security_group in cache_cluster.cache_security_groups %}
          <member>
            <CacheSecurityGroupName>{{ cache_security_group.cache_security_group_name }}</CacheSecurityGroupName>
            <Status>{{ cache_security_group.status }}</Status>
          </member>
{% endfor %}
        </CacheSecurityGroups>
        <CacheParameterGroup>{{ cache_cluster.cache_parameter_group }}</CacheParameterGroup>
        <CacheSubnetGroupName>{{ cache_cluster.cache_subnet_group_name }}</CacheSubnetGroupName>
        <CacheNodes>
{% for cache_node in cache_cluster.cache_nodes %}
          <member>
            <CacheNodeId>{{ cache_node.cache_node_id }}</CacheNodeId>
            <CacheNodeStatus>{{ cache_node.cache_node_status }}</CacheNodeStatus>
            <CacheNodeCreateTime>{{ cache_node.cache_node_create_time }}</CacheNodeCreateTime>
            <Endpoint>{{ cache_node.endpoint }}</Endpoint>
            <ParameterGroupStatus>{{ cache_node.parameter_group_status }}</ParameterGroupStatus>
            <SourceCacheNodeId>{{ cache_node.source_cache_node_id }}</SourceCacheNodeId>
            <CustomerAvailabilityZone>{{ cache_node.customer_availability_zone }}</CustomerAvailabilityZone>
            <CustomerOutpostArn>{{ cache_node.customer_outpost_arn }}</CustomerOutpostArn>
          </member>
{% endfor %}
        </CacheNodes>
        <AutoMinorVersionUpgrade>{{ cache_cluster.auto_minor_version_upgrade|lower }}</AutoMinorVersionUpgrade>
        <SecurityGroups>
{% for security_group in cache_cluster.security_groups %}
          <member>
            <SecurityGroupId>{{ security_group.security_group_id }}</SecurityGroupId>
            <Status>{{ security_group.status }}</Status>
          </member>
{% endfor %}
        </SecurityGroups>
        <ReplicationGroupId>{{ cache_cluster.replication_group_id }}</ReplicationGroupId>
        <SnapshotRetentionLimit>{{ cache_cluster.snapshot_retention_limit }}</SnapshotRetentionLimit>
        <SnapshotWindow>{{ cache_cluster.snapshot_window }}</SnapshotWindow>
        <AuthTokenEnabled>{{ cache_cluster.auth_token_enabled }}</AuthTokenEnabled>
        <AuthTokenLastModifiedDate>{{ cache_cluster.auth_token_last_modified_date }}</AuthTokenLastModifiedDate>
        <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
        <AtRestEncryptionEnabled>{{ cache_cluster.at_rest_encryption_enabled }}</AtRestEncryptionEnabled>
        <ARN>{{ cache_cluster.arn }}</ARN>
        <ReplicationGroupLogDeliveryEnabled>{{ cache_cluster.replication_group_log_delivery_enabled }}</ReplicationGroupLogDeliveryEnabled>
        <LogDeliveryConfigurations>
{% for log_delivery_configuration in cache_cluster.log_delivery_configurations %}
          <member>
            <LogType>{{ log_delivery_configuration.log_type }}</LogType>
            <DestinationType>{{ log_delivery_configuration.destination_type }}</DestinationType>
            <DestinationDetails>{{ log_delivery_configuration.destination_details }}</DestinationDetails>
            <LogFormat>{{ log_delivery_configuration.log_format }}</LogFormat>
            <Status>{{ log_delivery_configuration.status }}</Status>
            <Message>{{ log_delivery_configuration.message }}</Message>
          </member>
{% endfor %}
        </LogDeliveryConfigurations>
        <NetworkType>{{ cache_cluster.network_type }}</NetworkType>
        <IpDiscovery>{{ cache_cluster.ip_discovery }}</IpDiscovery>
        <TransitEncryptionMode>{{ cache_cluster.transit_encryption_mode }}</TransitEncryptionMode>
      </member>
{% endfor %}
    </CacheClusters>
  </DescribeCacheClustersResult>
</DescribeCacheClustersResponse>"""

DELETE_CACHE_CLUSTER_TEMPLATE = """<DeleteCacheClusterResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <DeleteCacheClusterResult>
    <CacheCluster>
  <CacheClusterId>{{ cache_cluster.cache_cluster_id }}</CacheClusterId>
  <ConfigurationEndpoint>
    <Address>example.cache.amazonaws.com</Address>
    <Port>{{ cache_cluster.port }}</Port>
  </ConfigurationEndpoint>
  <ClientDownloadLandingPage></ClientDownloadLandingPage>
  <CacheNodeType>{{ cache_cluster.cache_node_type }}</CacheNodeType>
  <Engine>{{ cache_cluster.engine }}</Engine>
  <EngineVersion>{{ cache_cluster.engine_version }}</EngineVersion>
  <CacheClusterStatus>available</CacheClusterStatus>
  <NumCacheNodes>{{ cache_cluster.num_cache_nodes }}</NumCacheNodes>
  <PreferredAvailabilityZone>{{ cache_cluster.preferred_availability_zone }}</PreferredAvailabilityZone>
  <PreferredOutpostArn>{{ cache_cluster.preferred_outpost_arn }}</PreferredOutpostArn>
  <CacheClusterCreateTime>{{ cache_cluster.cache_cluster_create_time }}</CacheClusterCreateTime>
  <PreferredMaintenanceWindow>{{ cache_cluster.preferred_maintenance_window }}</PreferredMaintenanceWindow>
  {% if cache_cluster.cache_node_ids_to_remove != [] %}
  <PendingModifiedValues>
    <NumCacheNodes>{{ cache_cluster.num_cache_nodes }}</NumCacheNodes>
    {% for cache_node_id_to_remove in cache_cluster.cache_node_ids_to_remove %}
    <CacheNodeIdsToRemove>{{ cache_node_id_to_remove }}</CacheNodeIdsToRemove>
    {% endfor %}
    <EngineVersion>{{ cache_cluster.engine_version }}</EngineVersion>
    <CacheNodeType>{{ cache_cluster.cache_node_type }}</CacheNodeType>
    <AuthTokenStatus>SETTING</AuthTokenStatus>
    <LogDeliveryConfigurations>
    {% for log_delivery_configuration in cache_cluster.log_delivery_configurations %}
      <LogType>{{ log_delivery_configuration.LogType }}</LogType>
      <DestinationType>{{ log_delivery_configuration.DestinationType }}</DestinationType>
      <DestinationDetails>
        <CloudWatchLogsDetails>
          <LogGroup>{{ log_delivery_configuration.LogGroup }}</LogGroup>
        </CloudWatchLogsDetails>
        <KinesisFirehoseDetails>
          <DeliveryStream>{{ log_delivery_configuration.DeliveryStream }}</DeliveryStream>
        </KinesisFirehoseDetails>
      </DestinationDetails>
      <LogFormat>{{ log_delivery_configuration.LogFormat }}</LogFormat>
      {% endfor %}
    </LogDeliveryConfigurations>
    <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
    <TransitEncryptionMode>preferred</TransitEncryptionMode>
  </PendingModifiedValues>
  {% endif %}
  <NotificationConfiguration>
    <TopicArn>{{ cache_cluster.notification_topic_arn }}</TopicArn>
    <TopicStatus>active</TopicStatus>
  </NotificationConfiguration>
  <CacheSecurityGroups>
  {% for cache_security_group_name in cache_cluster.cache_security_group_names %}
    <CacheSecurityGroupName>{{ cache_security_group_name }}</CacheSecurityGroupName>
    {% endfor %}
    <Status>active</Status>
  </CacheSecurityGroups>
  <CacheParameterGroup>
    <CacheParameterGroupName>{{ cache_cluster.cache_parameter_group_name }}</CacheParameterGroupName>
    <ParameterApplyStatus>active</ParameterApplyStatus>
    {% for cache_node_id_to_reboot in cache_cluster.cache_node_ids_to_reboot %}
    <CacheNodeIdsToReboot>
    {{ cache_node_id_to_reboot }}
    </CacheNodeIdsToReboot>
    {% endfor %}
  </CacheParameterGroup>
  <CacheSubnetGroupName>{{ cache_cluster.cache_subnet_group_name }}</CacheSubnetGroupName>
  <CacheNodes>
    <CacheNodeId>{{ cache_cluster.cache_node_id }}</CacheNodeId>
    <CacheNodeStatus>{{ cache_cluster.cache_node_status }}</CacheNodeStatus>
    <CacheNodeCreateTime>{{ cache_cluster.cache_cluster_create_time }}</CacheNodeCreateTime>
    <Endpoint>
      <Address>{{ cache_cluster.address }}</Address>
      <Port>{{ cache_cluster.port }}</Port>
    </Endpoint>
    <ParameterGroupStatus>active</ParameterGroupStatus>
    <SourceCacheNodeId>{{ cache_cluster.cache_node_id }}</SourceCacheNodeId>
    <CustomerAvailabilityZone>{{ cache_cluster.preferred_availability_zone }}</CustomerAvailabilityZone>
    <CustomerOutpostArn>{{ cache_cluster.preferred_output_arn }}</CustomerOutpostArn>
  </CacheNodes>
  <AutoMinorVersionUpgrade>{{ cache_cluster.auto_minor_version_upgrade|lower }}</AutoMinorVersionUpgrade>
  <SecurityGroups>
  {% for security_group_id in cache_cluster.security_group_ids %}
    <SecurityGroupId>{{ security_group_id }}</SecurityGroupId>
    <Status>active</Status>
    {% endfor %}
  </SecurityGroups>
  {% if cache_cluster.engine == "redis" %}
  <ReplicationGroupId>{{ cache_cluster.replication_group_id }}</ReplicationGroupId>
  <SnapshotRetentionLimit>{{ cache_cluster.snapshot_retention_limit }}</SnapshotRetentionLimit>
  <SnapshotWindow>{{ cache_cluster.snapshot_window }}</SnapshotWindow>
  {% endif %}
  <AuthTokenEnabled>true</AuthTokenEnabled>
  <AuthTokenLastModifiedDate>{{ cache_cluster.cache_cluster_create_time }}</AuthTokenLastModifiedDate>
  <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
  <AtRestEncryptionEnabled>true</AtRestEncryptionEnabled>
  <ARN>{{ cache_cluster.arn }}</ARN>
  <ReplicationGroupLogDeliveryEnabled>true</ReplicationGroupLogDeliveryEnabled>
  <LogDeliveryConfigurations>
  {% for log_delivery_configuration in cache_cluster.log_delivery_configurations %}
      <LogType>{{ log_delivery_configuration.LogType }}</LogType>
      <DestinationType>{{ log_delivery_configuration.DestinationType }}</DestinationType>
      <DestinationDetails>
        <CloudWatchLogsDetails>
          <LogGroup>{{ log_delivery_configuration.LogGroup }}</LogGroup>
        </CloudWatchLogsDetails>
        <KinesisFirehoseDetails>
          <DeliveryStream>{{ log_delivery_configuration.DeliveryStream }}</DeliveryStream>
        </KinesisFirehoseDetails>
      </DestinationDetails>
      <LogFormat>{{ log_delivery_configuration.LogFormat }}</LogFormat>
      <Status>active</Status>
      <Message></Message>
  {% endfor %}
  </LogDeliveryConfigurations>
  <NetworkType>{{ cache_cluster.network_type }}</NetworkType>
  <IpDiscovery>{{ cache_cluster.ip_discovery }}</IpDiscovery>
  <TransitEncryptionMode>preferred</TransitEncryptionMode>
</CacheCluster>
  </DeleteCacheClusterResult>
</DeleteCacheClusterResponse>"""

LIST_TAGS_FOR_RESOURCE_TEMPLATE = """<ListTagsForResourceResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ListTagsForResourceResult>
    <TagList>
    {%- for tag in tags -%}
      <Tag>
        <Key>{{ tag['Key'] }}</Key>
        <Value>{{ tag['Value'] }}</Value>
      </Tag>
    {%- endfor -%}
    </TagList>
  </ListTagsForResourceResult>
  <ResponseMetadata>
    <RequestId>8c21ba39-a598-11e4-b688-194eaf8658fa</RequestId>
  </ResponseMetadata>
</ListTagsForResourceResponse>"""

CREATE_CACHE_SUBNET_GROUP_TEMPLATE = """<CreateCacheSubnetGroupResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <CreateCacheSubnetGroupResult>
    <CacheSubnetGroup>
      <CacheSubnetGroupName>{{ cache_subnet_group.cache_subnet_group_name }}</CacheSubnetGroupName>
      <CacheSubnetGroupDescription>{{ cache_subnet_group.cache_subnet_group_description }}</CacheSubnetGroupDescription>
      <VpcId>{{ cache_subnet_group.vpc_id }}</VpcId>
      <Subnets>
        {% for subnet in cache_subnet_group.subnets_responses %}
        <Subnet>
          <SubnetIdentifier>{{ subnet.subnet_id }}</SubnetIdentifier>
          <SubnetAvailabilityZone>
            <Name>{{ subnet.subnet_az }}</Name>
          </SubnetAvailabilityZone>
          <SupportedNetworkTypes>
            {% for network_type in subnet.subnet_supported_network_types %}
              <member>{{ network_type }}</member>
            {% endfor %}
          </SupportedNetworkTypes>
        </Subnet>
        {% endfor %}
      </Subnets>
      <ARN>{{ cache_subnet_group.arn }}</ARN>
      <SupportedNetworkTypes>
        {% for network_type in cache_subnet_group.supported_network_types %}
          <member>{{ network_type }}</member>
        {% endfor %}
      </SupportedNetworkTypes>
    </CacheSubnetGroup>
  </CreateCacheSubnetGroupResult>
</CreateCacheSubnetGroupResponse>"""

DESCRIBE_CACHE_SUBNET_GROUPS_TEMPLATE = """<DescribeCacheSubnetGroupsResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <DescribeCacheSubnetGroupsResult>
    {% if marker %}<Marker>{{ marker }}</Marker>{% endif %}
    <CacheSubnetGroups>
      {% for cache_subnet_group in cache_subnet_groups %}
      <member>
        <CacheSubnetGroupName>{{ cache_subnet_group.cache_subnet_group_name }}</CacheSubnetGroupName>
        <CacheSubnetGroupDescription>{{ cache_subnet_group.cache_subnet_group_description }}</CacheSubnetGroupDescription>
        <VpcId>{{ cache_subnet_group.vpc_id }}</VpcId>
        <Subnets>
          {% for subnet in cache_subnet_group.subnets_responses %}
          <Subnet>
            <SubnetIdentifier>{{ subnet.subnet_id }}</SubnetIdentifier>
            <SubnetAvailabilityZone>
              <Name>{{ subnet.subnet_az }}</Name>
            </SubnetAvailabilityZone>
            <SupportedNetworkTypes>
              {% for network_type in subnet.subnet_supported_network_types %}
              <member>{{ network_type }}</member>
              {% endfor %}
            </SupportedNetworkTypes>
          </Subnet>
          {% endfor %}
        </Subnets>
        <ARN>{{ cache_subnet_group.arn }}</ARN>
        <SupportedNetworkTypes>
          {% for network_type in cache_subnet_group.supported_network_types %}
          <member>{{ network_type }}</member>
          {% endfor %}
        </SupportedNetworkTypes>
      </member>
      {% endfor %}
    </CacheSubnetGroups>
  </DescribeCacheSubnetGroupsResult>
</DescribeCacheSubnetGroupsResponse>"""

CREATE_REPLICATION_GROUP_TEMPLATE = """<CreateReplicationGroupResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <CreateReplicationGroupResult>
    <ReplicationGroup>
      <ReplicationGroupId>{{ replication_group.replication_group_id }}</ReplicationGroupId>
      <Description>{{ replication_group.replication_group_description }}</Description>
      {% if replication_group.global_replication_group_id %}
      <GlobalReplicationGroupInfo>
        <GlobalReplicationGroupId>{{ replication_group.global_replication_group_id }}</GlobalReplicationGroupId>
        <GlobalReplicationGroupMemberRole>{{ replication_group.global_replication_group_member_role }}</GlobalReplicationGroupMemberRole>
      </GlobalReplicationGroupInfo>
      {% endif %}
      <Status>{{ replication_group.status }}</Status>
      {% if replication_group.primary_cluster_id %}
      <PendingModifiedValues>
        <PrimaryClusterId>{{ replication_group.primary_cluster_id }}</PrimaryClusterId>
      </PendingModifiedValues>
      {% endif %}
      <MemberClusters>
        {% for member_cluster in replication_group.member_clusters %}
        <member>{{ member_cluster }}</member>
        {% endfor %}
      </MemberClusters>
      <NodeGroups>
        {% for node_group in replication_group.node_groups %}
        <member>
          <NodeGroupId>{{ node_group.node_group_id }}</NodeGroupId>
          <Status>{{ node_group.status }}</Status>
          {% if replication_group.cluster_mode == "enabled" %}
          <Slots>{{ node_group.slots }}</Slots>
          <NodeGroupMembers>
            {% for node in node_group.node_group_members %}
            <member>
              <CacheClusterId>{{ node.cache_cluster_id }}</CacheClusterId>
              <CacheNodeId>{{ node.cache_node_id }}</CacheNodeId>
              <PreferredAvailabilityZone>{{ node.preferred_availability_zone }}</PreferredAvailabilityZone>
            </member>
            {% endfor %}
          </NodeGroupMembers>
          {% endif %}
          {% if replication_group.cluster_mode == "disabled" %}
          <PrimaryEndpoint>
            <Address>{{ node_group.primary_endpoint_address }}</Address>
            <Port>{{ node_group.port }}</Port>
          </PrimaryEndpoint>
          <ReaderEndpoint>
            <Address>{{ node_group.reader_endpoint_address }}</Address>
            <Port>{{ node_group.port }}</Port>
          </ReaderEndpoint>
          <NodeGroupMembers>
          {% for node in node_group.node_group_members %}
          <member>
            <CacheClusterId>{{ node.cache_cluster_id }}</CacheClusterId>
            <CacheNodeId>{{ node.cache_node_id }}</CacheNodeId>
            <ReadEndpoint>
              <Address>{{ node.read_endpoint.address }}</Address>
              <Port>{{ node.read_endpoint.port }}</Port>
            </ReadEndpoint>
            <PreferredAvailabilityZone>{{ node.preferred_availability_zone }}</PreferredAvailabilityZone>
            <CurrentRole>{{ node.current_role }}</CurrentRole>
          </member>
          {% endfor %}
          </NodeGroupMembers>
          {% endif %}
        </member>
        {% endfor %}
      </NodeGroups>
      <SnapshottingClusterId>{{ replication_group.snapshotting_cluster_id }}</SnapshottingClusterId>
      <AutomaticFailover>{{ replication_group.automatic_failover }}</AutomaticFailover>
      <MultiAZ>{{ replication_group.multi_az }}</MultiAZ>
      {% if cluster_mode == "enabled" %}
      <ConfigurationEndpoint>
        <Address>{{ replication_group.configuration_endpoint.address }}</Address>
        <Port>{{ replication_group.configuration_endpoint.port }}</Port>
      </ConfigurationEndpoint>
      <MemberClustersOutpostArns>
        {% for outpost_arn in replication_group.member_clusters_outpost_arns %}
        <member>{{ outpost_arn }}</member>
        {% endfor %}
      </MemberClustersOutpostArns>
      {% endif %}
      <SnapshotRetentionLimit>{{ replication_group.snapshot_retention_limit }}</SnapshotRetentionLimit>
      <SnapshotWindow>{{ replication_group.snapshot_window }}</SnapshotWindow>
      <ClusterEnabled>{{ replication_group.cluster_enabled|lower }}</ClusterEnabled>
      <CacheNodeType>{{ replication_group.cache_node_type }}</CacheNodeType>
      {% if replication_group.auth_token_enabled %}
      <AuthTokenEnabled>{{ replication_group.auth_token_enabled }}</AuthTokenEnabled>
      <AuthTokenLastModifiedDate>{{ replication_group.auth_token_last_modified_date }}</AuthTokenLastModifiedDate>
      {% endif %}
      <TransitEncryptionEnabled>{{ replication_group.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
      <AtRestEncryptionEnabled>{{ replication_group.at_rest_encryption_enabled|lower }}</AtRestEncryptionEnabled>
      {% if replication_group.kms_key_id %}
      <KmsKeyId>{{ replication_group.kms_key_id }}</KmsKeyId>
      {% endif %}
      <ARN>{{ replication_group.arn }}</ARN>
      <UserGroupIds>
        {% for user_group_id in replication_group.user_group_ids %}
        <member>{{ user_group_id }}</member>
        {% endfor %}
      </UserGroupIds>
      {%if replication_group.log_delivery_configurations %}
      <LogDeliveryConfigurations>
        {% for log_delivery_configuration in replication_group.log_delivery_configurations %}
        <member>
          <LogType>{{ log_delivery_configuration.log_type }}</LogType>
          <DestinationType>{{ log_delivery_configuration.destination_type }}</DestinationType>
          <DestinationDetails>
            {% if log_delivery_configuration.destination_details.cloudwatch_log_group %}
            <CloudWatchLogsDetails>
              <LogGroup>{{ log_delivery_configuration.destination_details.cloudwatch_log_group }}</LogGroup>
            </CloudWatchLogsDetails>
            {% endif %}
            {% if log_delivery_configuration.destination_details.kinesis_stream %}
            <KinesisFirehoseDetails>
              <DeliveryStream>{{ log_delivery_configuration.destination_details.kinesis_stream }}</DeliveryStream>
            </KinesisFirehoseDetails>
            {% endif %}
          </DestinationDetails>
          <LogFormat>{{ log_delivery_configuration.log_format }}</LogFormat>
          <Status>{{ log_delivery_configuration.status }}</Status>
          <Message>{{ log_delivery_configuration.message }}</Message>
        </member>
        {% endfor %}
      </LogDeliveryConfigurations>
      {% endif %}
      <ReplicationGroupCreateTime>{{ replication_group.replication_group_create_time }}</ReplicationGroupCreateTime>
      <DataTiering>{{ replication_group.data_tiering }}</DataTiering>
      <AutoMinorVersionUpgrade>{{ replication_group.auto_minor_version_upgrade|lower }}</AutoMinorVersionUpgrade>
      <NetworkType>{{ replication_group.network_type }}</NetworkType>
      <IpDiscovery>{{ replication_group.ip_discovery }}</IpDiscovery>
      <TransitEncryptionMode>{{ replication_group.transit_encryption_mode }}</TransitEncryptionMode>
      <ClusterMode>{{ replication_group.cluster_mode }}</ClusterMode>
      <Engine>{{ replication_group.engine }}</Engine>
    </ReplicationGroup>
  </CreateReplicationGroupResult>
</CreateReplicationGroupResponse>"""


DESCRIBE_REPLICATION_GROUPS_TEMPLATE = """<DescribeReplicationGroupsResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <DescribeReplicationGroupsResult>
    {% if marker %}<Marker>{{ marker }}</Marker>{% endif %}
    <ReplicationGroups>
    {% for replication_group in replication_groups %}
      <member>
        <ReplicationGroupId>{{ replication_group.replication_group_id }}</ReplicationGroupId>
        <Description>{{ replication_group.replication_group_description }}</Description>
        {% if replication_group.global_replication_group_id %}
        <GlobalReplicationGroupInfo>
          <GlobalReplicationGroupId>{{ replication_group.global_replication_group_id }}</GlobalReplicationGroupId>
          <GlobalReplicationGroupMemberRole>{{ replication_group.global_replication_group_member_role }}</GlobalReplicationGroupMemberRole>
        </GlobalReplicationGroupInfo>
        {% endif %}
        <Status>{{ replication_group.status }}</Status>
        {% if replication_group.primary_cluster_id %}
        <PendingModifiedValues>
          <PrimaryClusterId>{{ replication_group.primary_cluster_id }}</PrimaryClusterId>
        </PendingModifiedValues>
        {% endif %}
        <MemberClusters>
          {% for member_cluster in replication_group.member_clusters %}
          <member>{{ member_cluster }}</member>
          {% endfor %}
        </MemberClusters>
        <NodeGroups>
        {% for node_group in replication_group.node_groups %}
          <member>
            <NodeGroupId>{{ node_group.node_group_id }}</NodeGroupId>
            <Status>{{ node_group.status }}</Status>
            {% if replication_group.cluster_mode == "enabled" %}
            <Slots>{{ node_group.slots }}</Slots>
            <NodeGroupMembers>
              {% for node in node_group.node_group_members %}
              <member>
                <CacheClusterId>{{ node.cache_cluster_id }}</CacheClusterId>
                <CacheNodeId>{{ node.cache_node_id }}</CacheNodeId>
                <PreferredAvailabilityZone>{{ node.preferred_availability_zone }}</PreferredAvailabilityZone>
              </member>
              {% endfor %}
            </NodeGroupMembers>
            {% endif %}
            {% if replication_group.cluster_mode == "disabled" %}
            <PrimaryEndpoint>
              <Address>{{ node_group.primary_endpoint_address }}</Address>
              <Port>{{ node_group.port }}</Port>
            </PrimaryEndpoint>
            <ReaderEndpoint>
              <Address>{{ node_group.reader_endpoint_address }}</Address>
              <Port>{{ node_group.port }}</Port>
            </ReaderEndpoint>
            <NodeGroupMembers>
            {% for node in node_group.node_group_members %}
              <member>
                <CacheClusterId>{{ node.cache_cluster_id }}</CacheClusterId>
                <CacheNodeId>{{ node.cache_node_id }}</CacheNodeId>
                <ReadEndpoint>
                  <Address>{{ node.read_endpoint.address }}</Address>
                  <Port>{{ node.read_endpoint.port }}</Port>
                </ReadEndpoint>
                <PreferredAvailabilityZone>{{ node.preferred_availability_zone }}</PreferredAvailabilityZone>
                <CurrentRole>{{ node.current_role }}</CurrentRole>
              </member>
            {% endfor %}
            </NodeGroupMembers>
            {% endif %}
          </member>
        {% endfor %}
        </NodeGroups>
        <SnapshottingClusterId>{{ replication_group.snapshotting_cluster_id }}</SnapshottingClusterId>
        <AutomaticFailover>{{ replication_group.automatic_failover }}</AutomaticFailover>
        <MultiAZ>{{ replication_group.multi_az }}</MultiAZ>
        {% if replication_group.cluster_mode == "enabled" %}
        <ConfigurationEndpoint>
          <Address>{{ replication_group.configuration_endpoint.address }}</Address>
          <Port>{{ replication_group.configuration_endpoint.port }}</Port>
        </ConfigurationEndpoint>
        <MemberClustersOutpostArns>
          {% for outpost_arn in replication_group.member_clusters_outpost_arns %}
          <member>{{ outpost_arn }}</member>
          {% endfor %}
        </MemberClustersOutpostArns>
        {% endif %}
        <SnapshotRetentionLimit>{{ replication_group.snapshot_retention_limit }}</SnapshotRetentionLimit>
        <SnapshotWindow>{{ replication_group.snapshot_window }}</SnapshotWindow>
        <ClusterEnabled>{{ replication_group.cluster_enabled|lower }}</ClusterEnabled>
        <CacheNodeType>{{ replication_group.cache_node_type }}</CacheNodeType>
        {% if replication_group.auth_token_enabled %}
        <AuthTokenEnabled>{{ replication_group.auth_token_enabled }}</AuthTokenEnabled>
        <AuthTokenLastModifiedDate>{{ replication_group.auth_token_last_modified_date }}</AuthTokenLastModifiedDate>
        {% endif %}
        <TransitEncryptionEnabled>{{ replication_group.transit_encryption_enabled|lower }}</TransitEncryptionEnabled>
        <AtRestEncryptionEnabled>{{ replication_group.at_rest_encryption_enabled|lower }}</AtRestEncryptionEnabled>
        {% if replication_group.kms_key_id %}
        <KmsKeyId>{{ replication_group.kms_key_id }}</KmsKeyId>
        {% endif %}
        <ARN>{{ replication_group.arn }}</ARN>
        <UserGroupIds>
          {% for user_group_id in replication_group.user_group_ids %}
          <member>{{ user_group_id }}</member>
          {% endfor %}
        </UserGroupIds>
        {%if replication_group.log_delivery_configurations %}
        <LogDeliveryConfigurations>
          {% for log_delivery_configuration in replication_group.log_delivery_configurations %}
          <member>
            <LogType>{{ log_delivery_configuration.log_type }}</LogType>
            <DestinationType>{{ log_delivery_configuration.destination_type }}</DestinationType>
            <DestinationDetails>
              {% if log_delivery_configuration.destination_details.cloudwatch_log_group %}
              <CloudWatchLogsDetails>
                <LogGroup>{{ log_delivery_configuration.destination_details.cloudwatch_log_group }}</LogGroup>
              </CloudWatchLogsDetails>
              {% endif %}
              {% if log_delivery_configuration.destination_details.kinesis_stream %}
              <KinesisFirehoseDetails>
                <DeliveryStream>{{ log_delivery_configuration.destination_details.kinesis_stream }}</DeliveryStream>
              </KinesisFirehoseDetails>
              {% endif %}
            </DestinationDetails>
            <LogFormat>{{ log_delivery_configuration.log_format }}</LogFormat>
            <Status>{{ log_delivery_configuration.status }}</Status>
            <Message>{{ log_delivery_configuration.message }}</Message>
          </member>
          {% endfor %}
        </LogDeliveryConfigurations>
        {% endif %}
        <ReplicationGroupCreateTime>{{ replication_group.replication_group_create_time }}</ReplicationGroupCreateTime>
        <DataTiering>{{ replication_group.data_tiering }}</DataTiering>
        <AutoMinorVersionUpgrade>{{ replication_group.auto_minor_version_upgrade|lower }}</AutoMinorVersionUpgrade>
        <NetworkType>{{ replication_group.network_type }}</NetworkType>
        <IpDiscovery>{{ replication_group.ip_discovery }}</IpDiscovery>
        <TransitEncryptionMode>{{ replication_group.transit_encryption_mode }}</TransitEncryptionMode>
        <ClusterMode>{{ replication_group.cluster_mode }}</ClusterMode>
        <Engine>{{ replication_group.engine }}</Engine>
      </member>
    {% endfor %}
    </ReplicationGroups>
  </DescribeReplicationGroupsResult>
</DescribeReplicationGroupsResponse>"""
