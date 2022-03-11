import copy
import datetime

from collections import OrderedDict
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from moto.utilities.utils import random_string
from moto.ec2 import ec2_backends
from .exceptions import (
    ClusterAlreadyExistsFaultError,
    ClusterNotFoundError,
    ClusterParameterGroupNotFoundError,
    ClusterSecurityGroupNotFoundError,
    ClusterSnapshotAlreadyExistsError,
    ClusterSnapshotNotFoundError,
    ClusterSubnetGroupNotFoundError,
    InvalidParameterCombinationError,
    InvalidParameterValueError,
    InvalidSubnetError,
    ResourceNotFoundFaultError,
    SnapshotCopyAlreadyDisabledFaultError,
    SnapshotCopyAlreadyEnabledFaultError,
    SnapshotCopyDisabledFaultError,
    SnapshotCopyGrantAlreadyExistsFaultError,
    SnapshotCopyGrantNotFoundFaultError,
    UnknownSnapshotCopyRegionFaultError,
    ClusterSecurityGroupNotFoundFaultError,
    InvalidClusterSnapshotStateFaultError,
)


from moto.core import ACCOUNT_ID


class TaggableResourceMixin(object):

    resource_type = None

    def __init__(self, region_name, tags):
        self.region = region_name
        self.tags = tags or []

    @property
    def resource_id(self):
        return None

    @property
    def arn(self):
        return "arn:aws:redshift:{region}:{account_id}:{resource_type}:{resource_id}".format(
            region=self.region,
            account_id=ACCOUNT_ID,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
        )

    def create_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def delete_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]
        return self.tags


class Cluster(TaggableResourceMixin, CloudFormationModel):

    resource_type = "cluster"

    def __init__(
        self,
        redshift_backend,
        cluster_identifier,
        node_type,
        master_username,
        master_user_password,
        db_name,
        cluster_type,
        cluster_security_groups,
        vpc_security_group_ids,
        cluster_subnet_group_name,
        availability_zone,
        preferred_maintenance_window,
        cluster_parameter_group_name,
        automated_snapshot_retention_period,
        port,
        cluster_version,
        allow_version_upgrade,
        number_of_nodes,
        publicly_accessible,
        encrypted,
        region_name,
        tags=None,
        iam_roles_arn=None,
        enhanced_vpc_routing=None,
        restored_from_snapshot=False,
        kms_key_id=None,
    ):
        super().__init__(region_name, tags)
        self.redshift_backend = redshift_backend
        self.cluster_identifier = cluster_identifier
        self.create_time = iso_8601_datetime_with_milliseconds(
            datetime.datetime.utcnow()
        )
        self.status = "available"
        self.node_type = node_type
        self.master_username = master_username
        self.master_user_password = master_user_password
        self.db_name = db_name if db_name else "dev"
        self.vpc_security_group_ids = vpc_security_group_ids
        self.enhanced_vpc_routing = (
            enhanced_vpc_routing if enhanced_vpc_routing is not None else False
        )
        self.cluster_subnet_group_name = cluster_subnet_group_name
        self.publicly_accessible = publicly_accessible
        self.encrypted = encrypted

        self.allow_version_upgrade = (
            allow_version_upgrade if allow_version_upgrade is not None else True
        )
        self.cluster_version = cluster_version if cluster_version else "1.0"
        self.port = int(port) if port else 5439
        self.automated_snapshot_retention_period = (
            int(automated_snapshot_retention_period)
            if automated_snapshot_retention_period
            else 1
        )
        self.preferred_maintenance_window = (
            preferred_maintenance_window
            if preferred_maintenance_window
            else "Mon:03:00-Mon:03:30"
        )

        if cluster_parameter_group_name:
            self.cluster_parameter_group_name = [cluster_parameter_group_name]
        else:
            self.cluster_parameter_group_name = ["default.redshift-1.0"]

        if cluster_security_groups:
            self.cluster_security_groups = cluster_security_groups
        else:
            self.cluster_security_groups = ["Default"]

        if availability_zone:
            self.availability_zone = availability_zone
        else:
            # This could probably be smarter, but there doesn't appear to be a
            # way to pull AZs for a region in boto
            self.availability_zone = region_name + "a"

        if cluster_type == "single-node":
            self.number_of_nodes = 1
        elif number_of_nodes:
            self.number_of_nodes = int(number_of_nodes)
        else:
            self.number_of_nodes = 1

        self.iam_roles_arn = iam_roles_arn or []
        self.restored_from_snapshot = restored_from_snapshot
        self.kms_key_id = kms_key_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-redshift-cluster.html
        return "AWS::Redshift::Cluster"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        redshift_backend = redshift_backends[region_name]
        properties = cloudformation_json["Properties"]

        if "ClusterSubnetGroupName" in properties:
            subnet_group_name = properties[
                "ClusterSubnetGroupName"
            ].cluster_subnet_group_name
        else:
            subnet_group_name = None

        cluster = redshift_backend.create_cluster(
            cluster_identifier=resource_name,
            node_type=properties.get("NodeType"),
            master_username=properties.get("MasterUsername"),
            master_user_password=properties.get("MasterUserPassword"),
            db_name=properties.get("DBName"),
            cluster_type=properties.get("ClusterType"),
            cluster_security_groups=properties.get("ClusterSecurityGroups", []),
            vpc_security_group_ids=properties.get("VpcSecurityGroupIds", []),
            cluster_subnet_group_name=subnet_group_name,
            availability_zone=properties.get("AvailabilityZone"),
            preferred_maintenance_window=properties.get("PreferredMaintenanceWindow"),
            cluster_parameter_group_name=properties.get("ClusterParameterGroupName"),
            automated_snapshot_retention_period=properties.get(
                "AutomatedSnapshotRetentionPeriod"
            ),
            port=properties.get("Port"),
            cluster_version=properties.get("ClusterVersion"),
            allow_version_upgrade=properties.get("AllowVersionUpgrade"),
            enhanced_vpc_routing=properties.get("EnhancedVpcRouting"),
            number_of_nodes=properties.get("NumberOfNodes"),
            publicly_accessible=properties.get("PubliclyAccessible"),
            encrypted=properties.get("Encrypted"),
            region_name=region_name,
            kms_key_id=properties.get("KmsKeyId"),
        )
        return cluster

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Endpoint.Address", "Endpoint.Port"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Endpoint.Address":
            return self.endpoint
        elif attribute_name == "Endpoint.Port":
            return self.port
        raise UnformattedGetAttTemplateException()

    @property
    def endpoint(self):
        return "{0}.cg034hpkmmjt.{1}.redshift.amazonaws.com".format(
            self.cluster_identifier, self.region
        )

    @property
    def security_groups(self):
        return [
            security_group
            for security_group in self.redshift_backend.describe_cluster_security_groups()
            if security_group.cluster_security_group_name
            in self.cluster_security_groups
        ]

    @property
    def vpc_security_groups(self):
        return [
            security_group
            for security_group in self.redshift_backend.ec2_backend.describe_security_groups()
            if security_group.id in self.vpc_security_group_ids
        ]

    @property
    def parameter_groups(self):
        return [
            parameter_group
            for parameter_group in self.redshift_backend.describe_cluster_parameter_groups()
            if parameter_group.cluster_parameter_group_name
            in self.cluster_parameter_group_name
        ]

    @property
    def resource_id(self):
        return self.cluster_identifier

    def pause(self):
        self.status = "paused"

    def resume(self):
        self.status = "available"

    def to_json(self):
        json_response = {
            "MasterUsername": self.master_username,
            "MasterUserPassword": "****",
            "ClusterVersion": self.cluster_version,
            "VpcSecurityGroups": [
                {"Status": "active", "VpcSecurityGroupId": group.id}
                for group in self.vpc_security_groups
            ],
            "ClusterSubnetGroupName": self.cluster_subnet_group_name,
            "AvailabilityZone": self.availability_zone,
            "ClusterStatus": self.status,
            "NumberOfNodes": self.number_of_nodes,
            "AutomatedSnapshotRetentionPeriod": self.automated_snapshot_retention_period,
            "PubliclyAccessible": self.publicly_accessible,
            "Encrypted": self.encrypted,
            "DBName": self.db_name,
            "PreferredMaintenanceWindow": self.preferred_maintenance_window,
            "ClusterParameterGroups": [
                {
                    "ParameterApplyStatus": "in-sync",
                    "ParameterGroupName": group.cluster_parameter_group_name,
                }
                for group in self.parameter_groups
            ],
            "ClusterSecurityGroups": [
                {
                    "Status": "active",
                    "ClusterSecurityGroupName": group.cluster_security_group_name,
                }
                for group in self.security_groups
            ],
            "Port": self.port,
            "NodeType": self.node_type,
            "ClusterIdentifier": self.cluster_identifier,
            "AllowVersionUpgrade": self.allow_version_upgrade,
            "Endpoint": {"Address": self.endpoint, "Port": self.port},
            "ClusterCreateTime": self.create_time,
            "PendingModifiedValues": [],
            "Tags": self.tags,
            "EnhancedVpcRouting": self.enhanced_vpc_routing,
            "IamRoles": [
                {"ApplyStatus": "in-sync", "IamRoleArn": iam_role_arn}
                for iam_role_arn in self.iam_roles_arn
            ],
            "KmsKeyId": self.kms_key_id,
        }
        if self.restored_from_snapshot:
            json_response["RestoreStatus"] = {
                "Status": "completed",
                "CurrentRestoreRateInMegaBytesPerSecond": 123.0,
                "SnapshotSizeInMegaBytes": 123,
                "ProgressInMegaBytes": 123,
                "ElapsedTimeInSeconds": 123,
                "EstimatedTimeToCompletionInSeconds": 123,
            }
        try:
            json_response[
                "ClusterSnapshotCopyStatus"
            ] = self.cluster_snapshot_copy_status
        except AttributeError:
            pass
        return json_response


class SnapshotCopyGrant(TaggableResourceMixin, BaseModel):

    resource_type = "snapshotcopygrant"

    def __init__(self, snapshot_copy_grant_name, kms_key_id):
        self.snapshot_copy_grant_name = snapshot_copy_grant_name
        self.kms_key_id = kms_key_id

    def to_json(self):
        return {
            "SnapshotCopyGrantName": self.snapshot_copy_grant_name,
            "KmsKeyId": self.kms_key_id,
        }


class SubnetGroup(TaggableResourceMixin, CloudFormationModel):

    resource_type = "subnetgroup"

    def __init__(
        self,
        ec2_backend,
        cluster_subnet_group_name,
        description,
        subnet_ids,
        region_name,
        tags=None,
    ):
        super().__init__(region_name, tags)
        self.ec2_backend = ec2_backend
        self.cluster_subnet_group_name = cluster_subnet_group_name
        self.description = description
        self.subnet_ids = subnet_ids
        if not self.subnets:
            raise InvalidSubnetError(subnet_ids)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-redshift-clustersubnetgroup.html
        return "AWS::Redshift::ClusterSubnetGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        redshift_backend = redshift_backends[region_name]
        properties = cloudformation_json["Properties"]

        subnet_group = redshift_backend.create_cluster_subnet_group(
            cluster_subnet_group_name=resource_name,
            description=properties.get("Description"),
            subnet_ids=properties.get("SubnetIds", []),
            region_name=region_name,
        )
        return subnet_group

    @property
    def subnets(self):
        return self.ec2_backend.get_all_subnets(filters={"subnet-id": self.subnet_ids})

    @property
    def vpc_id(self):
        return self.subnets[0].vpc_id

    @property
    def resource_id(self):
        return self.cluster_subnet_group_name

    def to_json(self):
        return {
            "VpcId": self.vpc_id,
            "Description": self.description,
            "ClusterSubnetGroupName": self.cluster_subnet_group_name,
            "SubnetGroupStatus": "Complete",
            "Subnets": [
                {
                    "SubnetStatus": "Active",
                    "SubnetIdentifier": subnet.id,
                    "SubnetAvailabilityZone": {"Name": subnet.availability_zone},
                }
                for subnet in self.subnets
            ],
            "Tags": self.tags,
        }


class SecurityGroup(TaggableResourceMixin, BaseModel):

    resource_type = "securitygroup"

    def __init__(
        self, cluster_security_group_name, description, region_name, tags=None
    ):
        super().__init__(region_name, tags)
        self.cluster_security_group_name = cluster_security_group_name
        self.description = description
        self.ingress_rules = []

    @property
    def resource_id(self):
        return self.cluster_security_group_name

    def to_json(self):
        return {
            "EC2SecurityGroups": [],
            "IPRanges": [],
            "Description": self.description,
            "ClusterSecurityGroupName": self.cluster_security_group_name,
            "Tags": self.tags,
        }


class ParameterGroup(TaggableResourceMixin, CloudFormationModel):

    resource_type = "parametergroup"

    def __init__(
        self,
        cluster_parameter_group_name,
        group_family,
        description,
        region_name,
        tags=None,
    ):
        super().__init__(region_name, tags)
        self.cluster_parameter_group_name = cluster_parameter_group_name
        self.group_family = group_family
        self.description = description

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-redshift-clusterparametergroup.html
        return "AWS::Redshift::ClusterParameterGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        redshift_backend = redshift_backends[region_name]
        properties = cloudformation_json["Properties"]

        parameter_group = redshift_backend.create_cluster_parameter_group(
            cluster_parameter_group_name=resource_name,
            description=properties.get("Description"),
            group_family=properties.get("ParameterGroupFamily"),
            region_name=region_name,
        )
        return parameter_group

    @property
    def resource_id(self):
        return self.cluster_parameter_group_name

    def to_json(self):
        return {
            "ParameterGroupFamily": self.group_family,
            "Description": self.description,
            "ParameterGroupName": self.cluster_parameter_group_name,
            "Tags": self.tags,
        }


class Snapshot(TaggableResourceMixin, BaseModel):

    resource_type = "snapshot"

    def __init__(
        self,
        cluster,
        snapshot_identifier,
        region_name,
        tags=None,
        iam_roles_arn=None,
        snapshot_type="manual",
    ):
        super().__init__(region_name, tags)
        self.cluster = copy.copy(cluster)
        self.snapshot_identifier = snapshot_identifier
        self.snapshot_type = snapshot_type
        self.status = "available"
        self.create_time = iso_8601_datetime_with_milliseconds(datetime.datetime.now())
        self.iam_roles_arn = iam_roles_arn or []

    @property
    def resource_id(self):
        return "{cluster_id}/{snapshot_id}".format(
            cluster_id=self.cluster.cluster_identifier,
            snapshot_id=self.snapshot_identifier,
        )

    def to_json(self):
        return {
            "SnapshotIdentifier": self.snapshot_identifier,
            "ClusterIdentifier": self.cluster.cluster_identifier,
            "SnapshotCreateTime": self.create_time,
            "Status": self.status,
            "Port": self.cluster.port,
            "AvailabilityZone": self.cluster.availability_zone,
            "MasterUsername": self.cluster.master_username,
            "ClusterVersion": self.cluster.cluster_version,
            "SnapshotType": self.snapshot_type,
            "NodeType": self.cluster.node_type,
            "NumberOfNodes": self.cluster.number_of_nodes,
            "DBName": self.cluster.db_name,
            "Tags": self.tags,
            "EnhancedVpcRouting": self.cluster.enhanced_vpc_routing,
            "IamRoles": [
                {"ApplyStatus": "in-sync", "IamRoleArn": iam_role_arn}
                for iam_role_arn in self.iam_roles_arn
            ],
        }


class RedshiftBackend(BaseBackend):
    def __init__(self, region_name):
        self.region = region_name
        self.clusters = {}
        self.subnet_groups = {}
        self.security_groups = {
            "Default": SecurityGroup(
                "Default", "Default Redshift Security Group", self.region
            )
        }
        self.parameter_groups = {
            "default.redshift-1.0": ParameterGroup(
                "default.redshift-1.0",
                "redshift-1.0",
                "Default Redshift parameter group",
                self.region,
            )
        }
        self.ec2_backend = ec2_backends[self.region]
        self.snapshots = OrderedDict()
        self.RESOURCE_TYPE_MAP = {
            "cluster": self.clusters,
            "parametergroup": self.parameter_groups,
            "securitygroup": self.security_groups,
            "snapshot": self.snapshots,
            "subnetgroup": self.subnet_groups,
        }
        self.snapshot_copy_grants = {}

    def reset(self):
        region_name = self.region
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "redshift"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "redshift-data", policy_supported=False
        )

    def enable_snapshot_copy(self, **kwargs):
        cluster_identifier = kwargs["cluster_identifier"]
        cluster = self.clusters[cluster_identifier]
        if not hasattr(cluster, "cluster_snapshot_copy_status"):
            if (
                cluster.encrypted == "true"
                and kwargs["snapshot_copy_grant_name"] is None
            ):
                raise InvalidParameterValueError(
                    "SnapshotCopyGrantName is required for Snapshot Copy on KMS encrypted clusters."
                )
            if kwargs["destination_region"] == self.region:
                raise UnknownSnapshotCopyRegionFaultError(
                    "Invalid region {}".format(self.region)
                )
            status = {
                "DestinationRegion": kwargs["destination_region"],
                "RetentionPeriod": kwargs["retention_period"],
                "SnapshotCopyGrantName": kwargs["snapshot_copy_grant_name"],
            }
            cluster.cluster_snapshot_copy_status = status
            return cluster
        else:
            raise SnapshotCopyAlreadyEnabledFaultError(cluster_identifier)

    def disable_snapshot_copy(self, **kwargs):
        cluster_identifier = kwargs["cluster_identifier"]
        cluster = self.clusters[cluster_identifier]
        if hasattr(cluster, "cluster_snapshot_copy_status"):
            del cluster.cluster_snapshot_copy_status
            return cluster
        else:
            raise SnapshotCopyAlreadyDisabledFaultError(cluster_identifier)

    def modify_snapshot_copy_retention_period(
        self, cluster_identifier, retention_period
    ):
        cluster = self.clusters[cluster_identifier]
        if hasattr(cluster, "cluster_snapshot_copy_status"):
            cluster.cluster_snapshot_copy_status["RetentionPeriod"] = retention_period
            return cluster
        else:
            raise SnapshotCopyDisabledFaultError(cluster_identifier)

    def create_cluster(self, **cluster_kwargs):
        cluster_identifier = cluster_kwargs["cluster_identifier"]
        if cluster_identifier in self.clusters:
            raise ClusterAlreadyExistsFaultError()
        cluster = Cluster(self, **cluster_kwargs)
        self.clusters[cluster_identifier] = cluster
        snapshot_id = "rs:{}-{}".format(
            cluster_identifier, datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        )
        # Automated snapshots don't copy over the tags
        self.create_cluster_snapshot(
            cluster_identifier,
            snapshot_id,
            cluster.region,
            None,
            snapshot_type="automated",
        )
        return cluster

    def pause_cluster(self, cluster_id):
        if cluster_id not in self.clusters:
            raise ClusterNotFoundError(cluster_identifier=cluster_id)
        self.clusters[cluster_id].pause()
        return self.clusters[cluster_id]

    def resume_cluster(self, cluster_id):
        if cluster_id not in self.clusters:
            raise ClusterNotFoundError(cluster_identifier=cluster_id)
        self.clusters[cluster_id].resume()
        return self.clusters[cluster_id]

    def describe_clusters(self, cluster_identifier=None):
        clusters = self.clusters.values()
        if cluster_identifier:
            if cluster_identifier in self.clusters:
                return [self.clusters[cluster_identifier]]
            else:
                raise ClusterNotFoundError(cluster_identifier)
        return clusters

    def modify_cluster(self, **cluster_kwargs):
        cluster_identifier = cluster_kwargs.pop("cluster_identifier")
        new_cluster_identifier = cluster_kwargs.pop("new_cluster_identifier", None)

        cluster_type = cluster_kwargs.get("cluster_type")
        if cluster_type and cluster_type not in ["multi-node", "single-node"]:
            raise InvalidParameterValueError(
                "Invalid cluster type. Cluster type can be one of multi-node or single-node"
            )
        if cluster_type == "single-node":
            # AWS will always silently override this value for single-node clusters.
            cluster_kwargs["number_of_nodes"] = 1
        elif cluster_type == "multi-node":
            if cluster_kwargs.get("number_of_nodes", 0) < 2:
                raise InvalidParameterCombinationError(
                    "Number of nodes for cluster type multi-node must be greater than or equal to 2"
                )

        cluster = self.describe_clusters(cluster_identifier)[0]

        for key, value in cluster_kwargs.items():
            setattr(cluster, key, value)

        if new_cluster_identifier:
            dic = {
                "cluster_identifier": cluster_identifier,
                "skip_final_snapshot": True,
                "final_cluster_snapshot_identifier": None,
            }
            self.delete_cluster(**dic)
            cluster.cluster_identifier = new_cluster_identifier
            self.clusters[new_cluster_identifier] = cluster

        return cluster

    def delete_automated_snapshots(self, cluster_identifier):
        snapshots = self.describe_cluster_snapshots(
            cluster_identifier=cluster_identifier
        )
        for snapshot in snapshots:
            if snapshot.snapshot_type == "automated":
                self.snapshots.pop(snapshot.snapshot_identifier)

    def delete_cluster(self, **cluster_kwargs):
        cluster_identifier = cluster_kwargs.pop("cluster_identifier")
        cluster_skip_final_snapshot = cluster_kwargs.pop("skip_final_snapshot")
        cluster_snapshot_identifer = cluster_kwargs.pop(
            "final_cluster_snapshot_identifier"
        )

        if cluster_identifier in self.clusters:
            if (
                cluster_skip_final_snapshot is False
                and cluster_snapshot_identifer is None
            ):
                raise InvalidParameterCombinationError(
                    "FinalClusterSnapshotIdentifier is required unless SkipFinalClusterSnapshot is specified."
                )
            elif (
                cluster_skip_final_snapshot is False
                and cluster_snapshot_identifer is not None
            ):  # create snapshot
                cluster = self.describe_clusters(cluster_identifier)[0]
                self.create_cluster_snapshot(
                    cluster_identifier,
                    cluster_snapshot_identifer,
                    cluster.region,
                    cluster.tags,
                )
            self.delete_automated_snapshots(cluster_identifier)
            return self.clusters.pop(cluster_identifier)
        raise ClusterNotFoundError(cluster_identifier)

    def create_cluster_subnet_group(
        self, cluster_subnet_group_name, description, subnet_ids, region_name, tags=None
    ):
        subnet_group = SubnetGroup(
            self.ec2_backend,
            cluster_subnet_group_name,
            description,
            subnet_ids,
            region_name,
            tags,
        )
        self.subnet_groups[cluster_subnet_group_name] = subnet_group
        return subnet_group

    def describe_cluster_subnet_groups(self, subnet_identifier=None):
        subnet_groups = self.subnet_groups.values()
        if subnet_identifier:
            if subnet_identifier in self.subnet_groups:
                return [self.subnet_groups[subnet_identifier]]
            else:
                raise ClusterSubnetGroupNotFoundError(subnet_identifier)
        return subnet_groups

    def delete_cluster_subnet_group(self, subnet_identifier):
        if subnet_identifier in self.subnet_groups:
            return self.subnet_groups.pop(subnet_identifier)
        raise ClusterSubnetGroupNotFoundError(subnet_identifier)

    def create_cluster_security_group(
        self, cluster_security_group_name, description, region_name, tags=None
    ):
        security_group = SecurityGroup(
            cluster_security_group_name, description, region_name, tags
        )
        self.security_groups[cluster_security_group_name] = security_group
        return security_group

    def describe_cluster_security_groups(self, security_group_name=None):
        security_groups = self.security_groups.values()
        if security_group_name:
            if security_group_name in self.security_groups:
                return [self.security_groups[security_group_name]]
            else:
                raise ClusterSecurityGroupNotFoundError(security_group_name)
        return security_groups

    def delete_cluster_security_group(self, security_group_identifier):
        if security_group_identifier in self.security_groups:
            return self.security_groups.pop(security_group_identifier)
        raise ClusterSecurityGroupNotFoundError(security_group_identifier)

    def authorize_cluster_security_group_ingress(self, security_group_name, cidr_ip):
        security_group = self.security_groups.get(security_group_name)
        if not security_group:
            raise ClusterSecurityGroupNotFoundFaultError()

        # just adding the cidr_ip as ingress rule for now as there is no security rule
        security_group.ingress_rules.append(cidr_ip)

        return security_group

    def create_cluster_parameter_group(
        self,
        cluster_parameter_group_name,
        group_family,
        description,
        region_name,
        tags=None,
    ):
        parameter_group = ParameterGroup(
            cluster_parameter_group_name, group_family, description, region_name, tags
        )
        self.parameter_groups[cluster_parameter_group_name] = parameter_group

        return parameter_group

    def describe_cluster_parameter_groups(self, parameter_group_name=None):
        parameter_groups = self.parameter_groups.values()
        if parameter_group_name:
            if parameter_group_name in self.parameter_groups:
                return [self.parameter_groups[parameter_group_name]]
            else:
                raise ClusterParameterGroupNotFoundError(parameter_group_name)
        return parameter_groups

    def delete_cluster_parameter_group(self, parameter_group_name):
        if parameter_group_name in self.parameter_groups:
            return self.parameter_groups.pop(parameter_group_name)
        raise ClusterParameterGroupNotFoundError(parameter_group_name)

    def create_cluster_snapshot(
        self,
        cluster_identifier,
        snapshot_identifier,
        region_name,
        tags,
        snapshot_type="manual",
    ):
        cluster = self.clusters.get(cluster_identifier)
        if not cluster:
            raise ClusterNotFoundError(cluster_identifier)
        if self.snapshots.get(snapshot_identifier) is not None:
            raise ClusterSnapshotAlreadyExistsError(snapshot_identifier)
        snapshot = Snapshot(
            cluster, snapshot_identifier, region_name, tags, snapshot_type=snapshot_type
        )
        self.snapshots[snapshot_identifier] = snapshot
        return snapshot

    def describe_cluster_snapshots(
        self, cluster_identifier=None, snapshot_identifier=None, snapshot_type=None
    ):
        snapshot_types = (
            ["automated", "manual"] if snapshot_type is None else [snapshot_type]
        )
        if cluster_identifier:
            cluster_snapshots = []
            for snapshot in self.snapshots.values():
                if snapshot.cluster.cluster_identifier == cluster_identifier:
                    if snapshot.snapshot_type in snapshot_types:
                        cluster_snapshots.append(snapshot)
            if cluster_snapshots:
                return cluster_snapshots

        if snapshot_identifier:
            if snapshot_identifier in self.snapshots:
                if self.snapshots[snapshot_identifier].snapshot_type in snapshot_types:
                    return [self.snapshots[snapshot_identifier]]
            raise ClusterSnapshotNotFoundError(snapshot_identifier)

        return self.snapshots.values()

    def delete_cluster_snapshot(self, snapshot_identifier):
        if snapshot_identifier not in self.snapshots:
            raise ClusterSnapshotNotFoundError(snapshot_identifier)

        snapshot = self.describe_cluster_snapshots(
            snapshot_identifier=snapshot_identifier
        )[0]
        if snapshot.snapshot_type == "automated":
            raise InvalidClusterSnapshotStateFaultError(snapshot_identifier)
        deleted_snapshot = self.snapshots.pop(snapshot_identifier)
        deleted_snapshot.status = "deleted"
        return deleted_snapshot

    def restore_from_cluster_snapshot(self, **kwargs):
        snapshot_identifier = kwargs.pop("snapshot_identifier")
        snapshot = self.describe_cluster_snapshots(
            snapshot_identifier=snapshot_identifier
        )[0]
        create_kwargs = {
            "node_type": snapshot.cluster.node_type,
            "master_username": snapshot.cluster.master_username,
            "master_user_password": snapshot.cluster.master_user_password,
            "db_name": snapshot.cluster.db_name,
            "cluster_type": "multi-node"
            if snapshot.cluster.number_of_nodes > 1
            else "single-node",
            "availability_zone": snapshot.cluster.availability_zone,
            "port": snapshot.cluster.port,
            "cluster_version": snapshot.cluster.cluster_version,
            "number_of_nodes": snapshot.cluster.number_of_nodes,
            "encrypted": snapshot.cluster.encrypted,
            "tags": snapshot.cluster.tags,
            "restored_from_snapshot": True,
            "enhanced_vpc_routing": snapshot.cluster.enhanced_vpc_routing,
        }
        create_kwargs.update(kwargs)
        return self.create_cluster(**create_kwargs)

    def create_snapshot_copy_grant(self, **kwargs):
        snapshot_copy_grant_name = kwargs["snapshot_copy_grant_name"]
        kms_key_id = kwargs["kms_key_id"]
        if snapshot_copy_grant_name not in self.snapshot_copy_grants:
            snapshot_copy_grant = SnapshotCopyGrant(
                snapshot_copy_grant_name, kms_key_id
            )
            self.snapshot_copy_grants[snapshot_copy_grant_name] = snapshot_copy_grant
            return snapshot_copy_grant
        raise SnapshotCopyGrantAlreadyExistsFaultError(snapshot_copy_grant_name)

    def delete_snapshot_copy_grant(self, **kwargs):
        snapshot_copy_grant_name = kwargs["snapshot_copy_grant_name"]
        if snapshot_copy_grant_name in self.snapshot_copy_grants:
            return self.snapshot_copy_grants.pop(snapshot_copy_grant_name)
        raise SnapshotCopyGrantNotFoundFaultError(snapshot_copy_grant_name)

    def describe_snapshot_copy_grants(self, **kwargs):
        copy_grants = self.snapshot_copy_grants.values()
        snapshot_copy_grant_name = kwargs["snapshot_copy_grant_name"]
        if snapshot_copy_grant_name:
            if snapshot_copy_grant_name in self.snapshot_copy_grants:
                return [self.snapshot_copy_grants[snapshot_copy_grant_name]]
            else:
                raise SnapshotCopyGrantNotFoundFaultError(snapshot_copy_grant_name)
        return copy_grants

    def _get_resource_from_arn(self, arn):
        try:
            arn_breakdown = arn.split(":")
            resource_type = arn_breakdown[5]
            if resource_type == "snapshot":
                resource_id = arn_breakdown[6].split("/")[1]
            else:
                resource_id = arn_breakdown[6]
        except IndexError:
            resource_type = resource_id = arn
        resources = self.RESOURCE_TYPE_MAP.get(resource_type)
        if resources is None:
            message = (
                "Tagging is not supported for this type of resource: '{0}' "
                "(the ARN is potentially malformed, please check the ARN "
                "documentation for more information)".format(resource_type)
            )
            raise ResourceNotFoundFaultError(message=message)
        try:
            resource = resources[resource_id]
        except KeyError:
            raise ResourceNotFoundFaultError(resource_type, resource_id)
        else:
            return resource

    @staticmethod
    def _describe_tags_for_resources(resources):
        tagged_resources = []
        for resource in resources:
            for tag in resource.tags:
                data = {
                    "ResourceName": resource.arn,
                    "ResourceType": resource.resource_type,
                    "Tag": {"Key": tag["Key"], "Value": tag["Value"]},
                }
                tagged_resources.append(data)
        return tagged_resources

    def _describe_tags_for_resource_type(self, resource_type):
        resources = self.RESOURCE_TYPE_MAP.get(resource_type)
        if not resources:
            raise ResourceNotFoundFaultError(resource_type=resource_type)
        return self._describe_tags_for_resources(resources.values())

    def _describe_tags_for_resource_name(self, resource_name):
        resource = self._get_resource_from_arn(resource_name)
        return self._describe_tags_for_resources([resource])

    def create_tags(self, resource_name, tags):
        resource = self._get_resource_from_arn(resource_name)
        resource.create_tags(tags)

    def describe_tags(self, resource_name, resource_type):
        if resource_name and resource_type:
            raise InvalidParameterValueError(
                "You cannot filter a list of resources using an Amazon "
                "Resource Name (ARN) and a resource type together in the "
                "same request. Retry the request using either an ARN or "
                "a resource type, but not both."
            )
        if resource_type:
            return self._describe_tags_for_resource_type(resource_type.lower())
        if resource_name:
            return self._describe_tags_for_resource_name(resource_name)
        # If name and type are not specified, return all tagged resources.
        # TODO: Implement aws marker pagination
        tagged_resources = []
        for resource_type in self.RESOURCE_TYPE_MAP:
            try:
                tagged_resources += self._describe_tags_for_resource_type(resource_type)
            except ResourceNotFoundFaultError:
                pass
        return tagged_resources

    def delete_tags(self, resource_name, tag_keys):
        resource = self._get_resource_from_arn(resource_name)
        resource.delete_tags(tag_keys)

    def get_cluster_credentials(
        self, cluster_identifier, db_user, auto_create, duration_seconds
    ):
        if duration_seconds < 900 or duration_seconds > 3600:
            raise InvalidParameterValueError(
                "Token duration must be between 900 and 3600 seconds"
            )
        expiration = datetime.datetime.now() + datetime.timedelta(0, duration_seconds)
        if cluster_identifier in self.clusters:
            user_prefix = "IAM:" if auto_create is False else "IAMA:"
            db_user = user_prefix + db_user
            return {
                "DbUser": db_user,
                "DbPassword": random_string(32),
                "Expiration": expiration,
            }
        else:
            raise ClusterNotFoundError(cluster_identifier)


redshift_backends = BackendDict(RedshiftBackend, "redshift")
