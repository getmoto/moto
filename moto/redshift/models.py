from __future__ import unicode_literals

import boto.redshift
from moto.core import BaseBackend
from moto.ec2 import ec2_backends
from .exceptions import (
    ClusterNotFoundError,
    ClusterSecurityGroupNotFoundError,
    ClusterSubnetGroupNotFoundError,
    InvalidSubnetError,
)


class Cluster(object):
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
        self.cluster_parameter_group_name = cluster_parameter_group_name
        self.publicly_accessible = publicly_accessible
        self.encrypted = encrypted

        self.allow_version_upgrade = allow_version_upgrade if allow_version_upgrade is not None else True
        self.cluster_version = cluster_version if cluster_version else "1.0"
        self.port = port if port else 5439
        self.automated_snapshot_retention_period = automated_snapshot_retention_period if automated_snapshot_retention_period else 1
        self.preferred_maintenance_window = preferred_maintenance_window if preferred_maintenance_window else "Mon:03:00-Mon:03:30"

        if cluster_security_groups:
            self.cluster_security_groups = cluster_security_groups
        else:
            self.cluster_security_groups = ["Default"]

        if availability_zone:
            self.availability_zone = availability_zone
        else:
            # This could probably be smarter, but there doesn't appear to be a
            # way to pull AZs for a region in boto
            self.availability_zone = region + "a"

        if cluster_type == 'single-node':
            self.number_of_nodes = 1
        elif number_of_nodes:
            self.number_of_nodes = number_of_nodes
        else:
            self.number_of_nodes = 1

    @property
    def security_groups(self):
        return [
            security_group for security_group
            in self.redshift_backend.describe_cluster_security_groups()
            if security_group.cluster_security_group_name in self.cluster_security_groups
        ]

    def to_json(self):
        return {
            "MasterUsername": self.master_username,
            "MasterUserPassword": "****",
            "ClusterVersion": self.cluster_version,
            "VpcSecurityGroups": [],
            "ClusterSubnetGroupName": self.cluster_subnet_group_name,
            "AvailabilityZone": self.availability_zone,
            "ClusterStatus": "creating",
            "NumberOfNodes": self.number_of_nodes,
            "AutomatedSnapshotRetentionPeriod": self.automated_snapshot_retention_period,
            "PubliclyAccessible": self.publicly_accessible,
            "Encrypted": self.encrypted,
            "DBName": self.db_name,
            "PreferredMaintenanceWindow": self.preferred_maintenance_window,
            "ClusterParameterGroups": [],
            "ClusterSecurityGroups": [{
                "Status": "active",
                "ClusterSecurityGroupName": group.cluster_security_group_name,
            } for group in self.security_groups],
            "Port": self.port,
            "NodeType": self.node_type,
            "ClusterIdentifier": self.cluster_identifier,
            "AllowVersionUpgrade": self.allow_version_upgrade,
        }


class SubnetGroup(object):

    def __init__(self, ec2_backend, cluster_subnet_group_name, description, subnet_ids):
        self.ec2_backend = ec2_backend
        self.cluster_subnet_group_name = cluster_subnet_group_name
        self.description = description
        self.subnet_ids = subnet_ids
        if not self.subnets:
            raise InvalidSubnetError(subnet_ids)

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


class SecurityGroup(object):
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


class RedshiftBackend(BaseBackend):

    def __init__(self, ec2_backend):
        self.clusters = {}
        self.subnet_groups = {}
        self.security_groups = {
            "Default": SecurityGroup("Default", "Default Redshift Security Group")
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
        new_cluster_identifier = cluster_kwargs.pop('new_cluster_identifier', None)

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
        subnet_group = SubnetGroup(self.ec2_backend, cluster_subnet_group_name, description, subnet_ids)
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
        security_group = SecurityGroup(cluster_security_group_name, description)
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


redshift_backends = {}
for region in boto.redshift.regions():
    redshift_backends[region.name] = RedshiftBackend(ec2_backends[region.name])
