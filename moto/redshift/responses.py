from __future__ import unicode_literals

import json
import dicttoxml

from moto.core.responses import BaseResponse
from .models import redshift_backends


class RedshiftResponse(BaseResponse):

    @property
    def redshift_backend(self):
        return redshift_backends[self.region]

    def get_response(self, response):
        if self.request_json:
            return json.dumps(response)
        else:
            xml = dicttoxml.dicttoxml(response, attr_type=False, root=False)
            return xml.decode("utf-8")

    def create_cluster(self):
        cluster_kwargs = {
            "cluster_identifier": self._get_param('ClusterIdentifier'),
            "node_type": self._get_param('NodeType'),
            "master_username": self._get_param('MasterUsername'),
            "master_user_password": self._get_param('MasterUserPassword'),
            "db_name": self._get_param('DBName'),
            "cluster_type": self._get_param('ClusterType'),
            "cluster_security_groups": self._get_multi_param('ClusterSecurityGroups.member'),
            "vpc_security_group_ids": self._get_multi_param('VpcSecurityGroupIds.member'),
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

        return self.get_response({
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

        return self.get_response({
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
            "cluster_security_groups": self._get_multi_param('ClusterSecurityGroups.member'),
            "vpc_security_group_ids": self._get_multi_param('VpcSecurityGroupIds.member'),
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

        return self.get_response({
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

        return self.get_response({
            "DeleteClusterResponse": {
                "DeleteClusterResult": {
                    "Cluster": cluster.to_json()
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def create_cluster_subnet_group(self):
        cluster_subnet_group_name = self._get_param('ClusterSubnetGroupName')
        description = self._get_param('Description')
        subnet_ids = self._get_multi_param('SubnetIds.member')

        subnet_group = self.redshift_backend.create_cluster_subnet_group(
            cluster_subnet_group_name=cluster_subnet_group_name,
            description=description,
            subnet_ids=subnet_ids,
        )

        return self.get_response({
            "CreateClusterSubnetGroupResponse": {
                "CreateClusterSubnetGroupResult": {
                    "ClusterSubnetGroup": subnet_group.to_json(),
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def describe_cluster_subnet_groups(self):
        subnet_identifier = self._get_param("ClusterSubnetGroupName")
        subnet_groups = self.redshift_backend.describe_cluster_subnet_groups(
            subnet_identifier)

        return self.get_response({
            "DescribeClusterSubnetGroupsResponse": {
                "DescribeClusterSubnetGroupsResult": {
                    "ClusterSubnetGroups": [subnet_group.to_json() for subnet_group in subnet_groups]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def delete_cluster_subnet_group(self):
        subnet_identifier = self._get_param("ClusterSubnetGroupName")
        self.redshift_backend.delete_cluster_subnet_group(subnet_identifier)

        return self.get_response({
            "DeleteClusterSubnetGroupResponse": {
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def create_cluster_security_group(self):
        cluster_security_group_name = self._get_param(
            'ClusterSecurityGroupName')
        description = self._get_param('Description')

        security_group = self.redshift_backend.create_cluster_security_group(
            cluster_security_group_name=cluster_security_group_name,
            description=description,
        )

        return self.get_response({
            "CreateClusterSecurityGroupResponse": {
                "CreateClusterSecurityGroupResult": {
                    "ClusterSecurityGroup": security_group.to_json(),
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def describe_cluster_security_groups(self):
        cluster_security_group_name = self._get_param(
            "ClusterSecurityGroupName")
        security_groups = self.redshift_backend.describe_cluster_security_groups(
            cluster_security_group_name)

        return self.get_response({
            "DescribeClusterSecurityGroupsResponse": {
                "DescribeClusterSecurityGroupsResult": {
                    "ClusterSecurityGroups": [security_group.to_json() for security_group in security_groups]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def delete_cluster_security_group(self):
        security_group_identifier = self._get_param("ClusterSecurityGroupName")
        self.redshift_backend.delete_cluster_security_group(
            security_group_identifier)

        return self.get_response({
            "DeleteClusterSecurityGroupResponse": {
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def create_cluster_parameter_group(self):
        cluster_parameter_group_name = self._get_param('ParameterGroupName')
        group_family = self._get_param('ParameterGroupFamily')
        description = self._get_param('Description')

        parameter_group = self.redshift_backend.create_cluster_parameter_group(
            cluster_parameter_group_name,
            group_family,
            description,
        )

        return self.get_response({
            "CreateClusterParameterGroupResponse": {
                "CreateClusterParameterGroupResult": {
                    "ClusterParameterGroup": parameter_group.to_json(),
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def describe_cluster_parameter_groups(self):
        cluster_parameter_group_name = self._get_param("ParameterGroupName")
        parameter_groups = self.redshift_backend.describe_cluster_parameter_groups(
            cluster_parameter_group_name)

        return self.get_response({
            "DescribeClusterParameterGroupsResponse": {
                "DescribeClusterParameterGroupsResult": {
                    "ParameterGroups": [parameter_group.to_json() for parameter_group in parameter_groups]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def delete_cluster_parameter_group(self):
        cluster_parameter_group_name = self._get_param("ParameterGroupName")
        self.redshift_backend.delete_cluster_parameter_group(
            cluster_parameter_group_name)

        return self.get_response({
            "DeleteClusterParameterGroupResponse": {
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })
