from __future__ import unicode_literals

import boto.redshift
from moto.core import BaseBackend
from .exceptions import ClusterNotFoundError


class Cluster(object):
    def __init__(self, cluster_identifier, node_type, master_username,
            master_user_password, db_name, cluster_type, cluster_security_groups,
            vpc_security_group_ids, cluster_subnet_group_name, availability_zone,
            preferred_maintenance_window, cluster_parameter_group_name,
            automated_snapshot_retention_period, port, cluster_version,
            allow_version_upgrade, number_of_nodes, publicly_accessible,
            encrypted, region):
        self.cluster_identifier = cluster_identifier
        self.node_type = node_type
        self.master_username = master_username
        self.master_user_password = master_user_password
        self.db_name = db_name if db_name else "dev"
        self.cluster_security_groups = cluster_security_groups
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
            "ClusterSecurityGroups": [],
            "Port": self.port,
            "NodeType": self.node_type,
            "ClusterIdentifier": self.cluster_identifier,
            "AllowVersionUpgrade": self.allow_version_upgrade,
        }


class RedshiftBackend(BaseBackend):

    def __init__(self):
        self.clusters = {}

    def create_cluster(self, **cluster_kwargs):
        cluster_identifier = cluster_kwargs['cluster_identifier']
        cluster = Cluster(**cluster_kwargs)
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


redshift_backends = {}
for region in boto.redshift.regions():
    redshift_backends[region.name] = RedshiftBackend()
