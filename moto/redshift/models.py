from __future__ import unicode_literals

import boto.redshift
from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends
from .exceptions import (
    ClusterNotFoundError,
    ClusterParameterGroupNotFoundError,
    ClusterSecurityGroupNotFoundError,
    ClusterSubnetGroupNotFoundError,
    InvalidSubnetError,
)


class Cluster(BaseModel):

    def __init__(self, redshift_backend, cluster_identifier, node_type, master_username,
                 master_user_password, db_name, cluster_type, cluster_security_groups,
                 vpc_security_group_ids, cluster_subnet_group_name, availability_zone,
                 preferred_maintenance_window, cluster_parameter_group_name,
                 automated_snapshot_retention_period, port, cluster_version,
                 allow_version_upgrade, number_of_nodes, publicly_accessible,
                 encrypted, region):
        self.redshift_backend = redshift_backend
        self.cluster_identifier = cluster_identifier
        self.node_type = node_type
        self.master_username = master_username
        self.master_user_password = master_user_password
        self.db_name = db_name if db_name else "dev"
        self.vpc_security_group_ids = vpc_security_group_ids
        self.cluster_subnet_group_name = cluster_subnet_group_name
        self.publicly_accessible = publicly_accessible
        self.encrypted = encrypted

        self.allow_version_upgrade = allow_version_upgrade if allow_version_upgrade is not None else True
        self.cluster_version = cluster_version if cluster_version else "1.0"
        self.port = int(port) if port else 5439
        self.automated_snapshot_retention_period = int(
            automated_snapshot_retention_period) if automated_snapshot_retention_period else 1
        self.preferred_maintenance_window = preferred_maintenance_window if preferred_maintenance_window else "Mon:03:00-Mon:03:30"

        if cluster_parameter_group_name:
            self.cluster_parameter_group_name = [cluster_parameter_group_name]
        else:
            self.cluster_parameter_group_name = ['default.redshift-1.0']

        if cluster_security_groups:
            self.cluster_security_groups = cluster_security_groups
        else:
            self.cluster_security_groups = ["Default"]

        self.region = region
        if availability_zone:
            self.availability_zone = availability_zone
        else:
            # This could probably be smarter, but there doesn't appear to be a
            # way to pull AZs for a region in boto
            self.availability_zone = region + "a"

        if cluster_type == 'single-node':
            self.number_of_nodes = 1
        elif number_of_nodes:
            self.number_of_nodes = int(number_of_nodes)
        else:
            self.number_of_nodes = 1

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        redshift_backend = redshift_backends[region_name]
        properties = cloudformation_json['Properties']

        if 'ClusterSubnetGroupName' in properties:
            subnet_group_name = properties[
                'ClusterSubnetGroupName'].cluster_subnet_group_name
        else:
            subnet_group_name = None
        cluster = redshift_backend.create_cluster(
            cluster_identifier=resource_name,
            node_type=properties.get('NodeType'),
            master_username=properties.get('MasterUsername'),
            master_user_password=properties.get('MasterUserPassword'),
            db_name=properties.get('DBName'),
            cluster_type=properties.get('ClusterType'),
            cluster_security_groups=properties.get(
                'ClusterSecurityGroups', []),
            vpc_security_group_ids=properties.get('VpcSecurityGroupIds', []),
            cluster_subnet_group_name=subnet_group_name,
            availability_zone=properties.get('AvailabilityZone'),
            preferred_maintenance_window=properties.get(
                'PreferredMaintenanceWindow'),
            cluster_parameter_group_name=properties.get(
                'ClusterParameterGroupName'),
            automated_snapshot_retention_period=properties.get(
                'AutomatedSnapshotRetentionPeriod'),
            port=properties.get('Port'),
            cluster_version=properties.get('ClusterVersion'),
            allow_version_upgrade=properties.get('AllowVersionUpgrade'),
            number_of_nodes=properties.get('NumberOfNodes'),
            publicly_accessible=properties.get("PubliclyAccessible"),
            encrypted=properties.get("Encrypted"),
            region=region_name,
        )
        return cluster

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Endpoint.Address':
            return self.endpoint
        elif attribute_name == 'Endpoint.Port':
            return self.port
        raise UnformattedGetAttTemplateException()

    @property
    def endpoint(self):
        return "{0}.cg034hpkmmjt.{1}.redshift.amazonaws.com".format(
            self.cluster_identifier,
            self.region,
        )

    @property
    def security_groups(self):
        return [
            security_group for security_group
            in self.redshift_backend.describe_cluster_security_groups()
            if security_group.cluster_security_group_name in self.cluster_security_groups
        ]

    @property
    def vpc_security_groups(self):
        return [
            security_group for security_group
            in self.redshift_backend.ec2_backend.describe_security_groups()
            if security_group.id in self.vpc_security_group_ids
        ]

    @property
    def parameter_groups(self):
        return [
            parameter_group for parameter_group
            in self.redshift_backend.describe_cluster_parameter_groups()
            if parameter_group.cluster_parameter_group_name in self.cluster_parameter_group_name
        ]

    def to_json(self):
        return {
            "MasterUsername": self.master_username,
            "MasterUserPassword": "****",
            "ClusterVersion": self.cluster_version,
            "VpcSecurityGroups": [{
                "Status": "active",
                "VpcSecurityGroupId": group.id
            } for group in self.vpc_security_groups],
            "ClusterSubnetGroupName": self.cluster_subnet_group_name,
            "AvailabilityZone": self.availability_zone,
            "ClusterStatus": "creating",
            "NumberOfNodes": self.number_of_nodes,
            "AutomatedSnapshotRetentionPeriod": self.automated_snapshot_retention_period,
            "PubliclyAccessible": self.publicly_accessible,
            "Encrypted": self.encrypted,
            "DBName": self.db_name,
            "PreferredMaintenanceWindow": self.preferred_maintenance_window,
            "ClusterParameterGroups": [{
                "ParameterApplyStatus": "in-sync",
                "ParameterGroupName": group.cluster_parameter_group_name,
            } for group in self.parameter_groups],
            "ClusterSecurityGroups": [{
                "Status": "active",
                "ClusterSecurityGroupName": group.cluster_security_group_name,
            } for group in self.security_groups],
            "Port": self.port,
            "NodeType": self.node_type,
            "ClusterIdentifier": self.cluster_identifier,
            "AllowVersionUpgrade": self.allow_version_upgrade,
        }


class SubnetGroup(BaseModel):

    def __init__(self, ec2_backend, cluster_subnet_group_name, description, subnet_ids):
        self.ec2_backend = ec2_backend
        self.cluster_subnet_group_name = cluster_subnet_group_name
        self.description = description
        self.subnet_ids = subnet_ids
        if not self.subnets:
            raise InvalidSubnetError(subnet_ids)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        redshift_backend = redshift_backends[region_name]
        properties = cloudformation_json['Properties']

        subnet_group = redshift_backend.create_cluster_subnet_group(
            cluster_subnet_group_name=resource_name,
            description=properties.get("Description"),
            subnet_ids=properties.get("SubnetIds", []),
        )
        return subnet_group

    @property
    def subnets(self):
        return self.ec2_backend.get_all_subnets(filters={'subnet-id': self.subnet_ids})

    @property
    def vpc_id(self):
        return self.subnets[0].vpc_id

    def to_json(self):
        return {
            "VpcId": self.vpc_id,
            "Description": self.description,
            "ClusterSubnetGroupName": self.cluster_subnet_group_name,
            "SubnetGroupStatus": "Complete",
            "Subnets": [{
                "SubnetStatus": "Active",
                "SubnetIdentifier": subnet.id,
                "SubnetAvailabilityZone": {
                    "Name": subnet.availability_zone
                },
            } for subnet in self.subnets],
        }


class SecurityGroup(BaseModel):

    def __init__(self, cluster_security_group_name, description):
        self.cluster_security_group_name = cluster_security_group_name
        self.description = description

    def to_json(self):
        return {
            "EC2SecurityGroups": [],
            "IPRanges": [],
            "Description": self.description,
            "ClusterSecurityGroupName": self.cluster_security_group_name,
        }


class ParameterGroup(BaseModel):

    def __init__(self, cluster_parameter_group_name, group_family, description):
        self.cluster_parameter_group_name = cluster_parameter_group_name
        self.group_family = group_family
        self.description = description

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        redshift_backend = redshift_backends[region_name]
        properties = cloudformation_json['Properties']

        parameter_group = redshift_backend.create_cluster_parameter_group(
            cluster_parameter_group_name=resource_name,
            description=properties.get("Description"),
            group_family=properties.get("ParameterGroupFamily"),
        )
        return parameter_group

    def to_json(self):
        return {
            "ParameterGroupFamily": self.group_family,
            "Description": self.description,
            "ParameterGroupName": self.cluster_parameter_group_name,
        }


class RedshiftBackend(BaseBackend):

    def __init__(self, ec2_backend):
        self.clusters = {}
        self.subnet_groups = {}
        self.security_groups = {
            "Default": SecurityGroup("Default", "Default Redshift Security Group")
        }
        self.parameter_groups = {
            "default.redshift-1.0": ParameterGroup(
                "default.redshift-1.0",
                "redshift-1.0",
                "Default Redshift parameter group",
            )
        }
        self.ec2_backend = ec2_backend

    def reset(self):
        ec2_backend = self.ec2_backend
        self.__dict__ = {}
        self.__init__(ec2_backend)

    def create_cluster(self, **cluster_kwargs):
        cluster_identifier = cluster_kwargs['cluster_identifier']
        cluster = Cluster(self, **cluster_kwargs)
        self.clusters[cluster_identifier] = cluster
        return cluster

    def describe_clusters(self, cluster_identifier=None):
        clusters = self.clusters.values()
        if cluster_identifier:
            if cluster_identifier in self.clusters:
                return [self.clusters[cluster_identifier]]
            else:
                raise ClusterNotFoundError(cluster_identifier)
        return clusters

    def modify_cluster(self, **cluster_kwargs):
        cluster_identifier = cluster_kwargs.pop('cluster_identifier')
        new_cluster_identifier = cluster_kwargs.pop(
            'new_cluster_identifier', None)

        cluster = self.describe_clusters(cluster_identifier)[0]

        for key, value in cluster_kwargs.items():
            setattr(cluster, key, value)

        if new_cluster_identifier:
            self.delete_cluster(cluster_identifier)
            cluster.cluster_identifier = new_cluster_identifier
            self.clusters[new_cluster_identifier] = cluster

        return cluster

    def delete_cluster(self, cluster_identifier):
        if cluster_identifier in self.clusters:
            return self.clusters.pop(cluster_identifier)
        raise ClusterNotFoundError(cluster_identifier)

    def create_cluster_subnet_group(self, cluster_subnet_group_name, description, subnet_ids):
        subnet_group = SubnetGroup(
            self.ec2_backend, cluster_subnet_group_name, description, subnet_ids)
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

    def create_cluster_security_group(self, cluster_security_group_name, description):
        security_group = SecurityGroup(
            cluster_security_group_name, description)
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

    def create_cluster_parameter_group(self, cluster_parameter_group_name,
                                       group_family, description):
        parameter_group = ParameterGroup(
            cluster_parameter_group_name, group_family, description)
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


redshift_backends = {}
for region in boto.redshift.regions():
    redshift_backends[region.name] = RedshiftBackend(ec2_backends[region.name])
