from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import redshift_backends


class RedshiftResponse(BaseResponse):

    @property
    def redshift_backend(self):
        return redshift_backends[self.region]

    def create_cluster(self):
        cluster_kwargs = {
            "cluster_identifier": self._get_param('ClusterIdentifier'),
            "node_type": self._get_param('NodeType'),
            "master_username": self._get_param('MasterUsername'),
            "master_user_password": self._get_param('MasterUserPassword'),
            "db_name": self._get_param('DBName'),
            "cluster_type": self._get_param('ClusterType'),
            "cluster_security_groups": self._get_multi_param('ClusterSecurityGroups'),
            "vpc_security_group_ids": self._get_multi_param('VpcSecurityGroupIds'),
            "cluster_subnet_group_name": self._get_param('ClusterSubnetGroupName'),
            "availability_zone": self._get_param('AvailabilityZone'),
            "preferred_maintenance_window": self._get_param('PreferredMaintenanceWindow'),
            "cluster_parameter_group_name": self._get_param('ClusterParameterGroupName'),
            "automated_snapshot_retention_period": self._get_int_param('AutomatedSnapshotRetentionPeriod'),
            "port": self._get_int_param('Port'),
            "cluster_version": self._get_param('ClusterVersion'),
            "allow_version_upgrade": self._get_bool_param('AllowVersionUpgrade'),
            "number_of_nodes": self._get_int_param('NumberOfNodes'),
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "encrypted": self._get_param("Encrypted"),
            "region": self.region,
        }

        cluster = self.redshift_backend.create_cluster(**cluster_kwargs)

        return json.dumps({
            "CreateClusterResponse": {
                "CreateClusterResult": {
                    "Cluster": cluster.to_json(),
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def describe_clusters(self):
        cluster_identifier = self._get_param("ClusterIdentifier")
        clusters = self.redshift_backend.describe_clusters(cluster_identifier)

        return json.dumps({
            "DescribeClustersResponse": {
                "DescribeClustersResult": {
                    "Clusters": [cluster.to_json() for cluster in clusters]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def modify_cluster(self):
        cluster_kwargs = {
            "cluster_identifier": self._get_param('ClusterIdentifier'),
            "new_cluster_identifier": self._get_param('NewClusterIdentifier'),
            "node_type": self._get_param('NodeType'),
            "master_user_password": self._get_param('MasterUserPassword'),
            "cluster_type": self._get_param('ClusterType'),
            "cluster_security_groups": self._get_multi_param('ClusterSecurityGroups'),
            "vpc_security_group_ids": self._get_multi_param('VpcSecurityGroupIds'),
            "cluster_subnet_group_name": self._get_param('ClusterSubnetGroupName'),
            "preferred_maintenance_window": self._get_param('PreferredMaintenanceWindow'),
            "cluster_parameter_group_name": self._get_param('ClusterParameterGroupName'),
            "automated_snapshot_retention_period": self._get_int_param('AutomatedSnapshotRetentionPeriod'),
            "cluster_version": self._get_param('ClusterVersion'),
            "allow_version_upgrade": self._get_bool_param('AllowVersionUpgrade'),
            "number_of_nodes": self._get_int_param('NumberOfNodes'),
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "encrypted": self._get_param("Encrypted"),
        }

        cluster = self.redshift_backend.modify_cluster(**cluster_kwargs)

        return json.dumps({
            "ModifyClusterResponse": {
                "ModifyClusterResult": {
                    "Cluster": cluster.to_json(),
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def delete_cluster(self):
        cluster_identifier = self._get_param("ClusterIdentifier")
        cluster = self.redshift_backend.delete_cluster(cluster_identifier)

        return json.dumps({
            "DeleteClusterResponse": {
                "DeleteClusterResult": {
                    "Cluster": cluster.to_json()
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })
