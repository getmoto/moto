from moto.core.responses import BaseResponse

from .exceptions import PasswordTooShort, PasswordRequired
from .models import elasticache_backends, ElastiCacheBackend


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
        engine = params.get("Engine")
        passwords = params.get("Passwords", [])
        no_password_required = self._get_bool_param("NoPasswordRequired", False)
        password_required = not no_password_required
        if password_required and not passwords:
            raise PasswordRequired
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

    def create_cache_cluster(self):
        params = self._get_params()
        cache_cluster_id = params.get("CacheClusterId")
        replication_group_id = params.get("ReplicationGroupId")
        az_mode = params.get("AZMode")
        preferred_availability_zone = params.get("PreferredAvailabilityZone")
        preferred_availability_zones = params.get("PreferredAvailabilityZones")
        num_cache_nodes = self._get_int_param("NumCacheNodes")
        cache_node_type = params.get("CacheNodeType")
        engine = params.get("Engine")
        engine_version = params.get("EngineVersion")
        cache_parameter_group_name = params.get("CacheParameterGroupName")
        cache_subnet_group_name = params.get("CacheSubnetGroupName")
        cache_security_group_names = params.get("CacheSecurityGroupNames")
        security_group_ids = params.get("SecurityGroupIds")
        tags = params.get("Tags")
        snapshot_arns = params.get("SnapshotArns")
        snapshot_name = params.get("SnapshotName")
        preferred_maintenance_window = params.get("PreferredMaintenanceWindow")
        port = params.get("Port")
        notification_topic_arn = params.get("NotificationTopicArn")
        auto_minor_version_upgrade = self._get_bool_param("AutoMinorVersionUpgrade")
        snapshot_retention_limit = self._get_int_param("SnapshotRetentionLimit")
        snapshot_window = params.get("SnapshotWindow")
        auth_token = params.get("AuthToken")
        outpost_mode = params.get("OutpostMode")
        preferred_outpost_arn = params.get("PreferredOutpostArn")
        preferred_outpost_arns = params.get("PreferredOutpostArns")
        log_delivery_configurations = params.get("LogDeliveryConfigurations")
        transit_encryption_enabled = self._get_bool_param("TransitEncryptionEnabled")
        network_type = params.get("NetworkType")
        ip_discovery = params.get("IpDiscovery")
        cache_node_ids_to_remove = []
        cache_node_ids_to_reboot = []
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
            cache_node_ids_to_reboot=cache_node_ids_to_reboot
        )
        template = self.response_template(CREATE_CACHE_CLUSTER_TEMPLATE)
        return template.render(cache_cluster=cache_cluster)


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
      <Type>password</Type>
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
    <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled }}</TransitEncryptionEnabled>
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
  <AutoMinorVersionUpgrade>{{ cache_cluster.auto_minor_version_upgrade }}</AutoMinorVersionUpgrade>
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
  <TransitEncryptionEnabled>{{ cache_cluster.transit_encryption_enabled }}</TransitEncryptionEnabled>
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
