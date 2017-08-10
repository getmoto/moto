from __future__ import unicode_literals

import json

import dicttoxml
from jinja2 import Template
from six import iteritems

from moto.core.responses import BaseResponse
from .models import redshift_backends


def convert_json_error_to_xml(json_error):
    error = json.loads(json_error)
    code = error['Error']['Code']
    message = error['Error']['Message']
    template = Template("""
        <RedshiftClientError>
            <Error>
              <Code>{{ code }}</Code>
              <Message>{{ message }}</Message>
              <Type>Sender</Type>
            </Error>
            <RequestId>6876f774-7273-11e4-85dc-39e55ca848d1</RequestId>
        </RedshiftClientError>""")
    return template.render(code=code, message=message)


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

    def call_action(self):
        status, headers, body = super(RedshiftResponse, self).call_action()
        if status >= 400 and not self.request_json:
            body = convert_json_error_to_xml(body)
        return status, headers, body

    def unpack_complex_list_params(self, label, names):
        unpacked_list = list()
        count = 1
        while self._get_param('{0}.{1}.{2}'.format(label, count, names[0])):
            param = dict()
            for i in range(len(names)):
                param[names[i]] = self._get_param(
                    '{0}.{1}.{2}'.format(label, count, names[i]))
            unpacked_list.append(param)
            count += 1
        return unpacked_list

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
        cluster = self.redshift_backend.create_cluster(**cluster_kwargs).to_json()
        cluster['ClusterStatus'] = 'creating'
        return self.get_response({
            "CreateClusterResponse": {
                "CreateClusterResult": {
                    "Cluster": cluster,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def restore_from_cluster_snapshot(self):
        snapshot_identifier = self._get_param('SnapshotIdentifier')
        snapshots = self.redshift_backend.describe_snapshots(
            None,
            snapshot_identifier)
        snapshot = snapshots[0]
        kwargs_from_snapshot = {
            "node_type": snapshot.cluster.node_type,
            "master_username": snapshot.cluster.master_username,
            "master_user_password": snapshot.cluster.master_user_password,
            "db_name": snapshot.cluster.db_name,
            "cluster_type": 'multi-node' if snapshot.cluster.number_of_nodes > 1 else 'single-node',
            "availability_zone": snapshot.cluster.availability_zone,
            "port": snapshot.cluster.port,
            "cluster_version": snapshot.cluster.cluster_version,
            "number_of_nodes": snapshot.cluster.number_of_nodes,
        }
        kwargs_from_request = {
            "cluster_identifier": self._get_param('ClusterIdentifier'),
            "port": self._get_int_param('Port'),
            "availability_zone": self._get_param('AvailabilityZone'),
            "allow_version_upgrade": self._get_bool_param(
                'AllowVersionUpgrade'),
            "cluster_subnet_group_name": self._get_param(
                'ClusterSubnetGroupName'),
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "cluster_parameter_group_name": self._get_param(
                'ClusterParameterGroupName'),
            "cluster_security_groups": self._get_multi_param(
                'ClusterSecurityGroups.member'),
            "vpc_security_group_ids": self._get_multi_param(
                'VpcSecurityGroupIds.member'),
            "preferred_maintenance_window": self._get_param(
                'PreferredMaintenanceWindow'),
            "automated_snapshot_retention_period": self._get_int_param(
                'AutomatedSnapshotRetentionPeriod'),
            "region": self.region,
            "encrypted": False,
        }
        kwargs_from_snapshot.update(kwargs_from_request)
        cluster_kwargs = kwargs_from_snapshot
        cluster = self.redshift_backend.create_cluster(**cluster_kwargs).to_json()
        cluster['ClusterStatus'] = 'creating'
        return self.get_response({
            "RestoreFromClusterSnapshotResponse": {
                "RestoreFromClusterSnapshotResult": {
                    "Cluster": cluster,
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
        request_kwargs = {
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
        # There's a bug in boto3 where the security group ids are not passed
        # according to the AWS documentation
        if not request_kwargs['vpc_security_group_ids']:
            request_kwargs['vpc_security_group_ids'] = self._get_multi_param(
                'VpcSecurityGroupIds.VpcSecurityGroupId')

        cluster_kwargs = {}
        # We only want parameters that were actually passed in, otherwise
        # we'll stomp all over our cluster metadata with None values.
        for (key, value) in iteritems(request_kwargs):
            if value is not None and value != []:
                cluster_kwargs[key] = value

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
        # There's a bug in boto3 where the subnet ids are not passed
        # according to the AWS documentation
        if not subnet_ids:
            subnet_ids = self._get_multi_param('SubnetIds.SubnetIdentifier')

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

    def create_cluster_snapshot(self):
        cluster_identifier = self._get_param('ClusterIdentifier')
        snapshot_identifier = self._get_param('SnapshotIdentifier')
        tags = self.unpack_complex_list_params(
            'Tags.Tag', ('Key', 'Value'))
        snapshot = self.redshift_backend.create_snapshot(cluster_identifier,
                                                         snapshot_identifier,
                                                         tags)
        return self.get_response({
            'CreateClusterSnapshotResponse': {
                "CreateClusterSnapshotResult": {
                    "Snapshot": snapshot.to_json(),
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def describe_cluster_snapshots(self):
        cluster_identifier = self._get_param('ClusterIdentifier')
        snapshot_identifier = self._get_param('DBSnapshotIdentifier')
        snapshots = self.redshift_backend.describe_snapshots(cluster_identifier,
                                                             snapshot_identifier)
        return self.get_response({
            "DescribeClusterSnapshotsResponse": {
                "DescribeClusterSnapshotsResult": {
                    "Snapshots": [snapshot.to_json() for snapshot in snapshots]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def delete_cluster_snapshot(self):
        snapshot_identifier = self._get_param('SnapshotIdentifier')
        snapshot = self.redshift_backend.delete_snapshot(snapshot_identifier)

        return self.get_response({
            "DeleteClusterSnapshotResponse": {
                "DeleteClusterSnapshotResult": {
                    "Snapshot": snapshot.to_json()
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def describe_tags(self):
        resource_type = self._get_param('ResourceType')
        if resource_type != 'Snapshot':
            raise NotImplementedError(
                "The describe_tags action has not been fully implemented.")
        tagged_resources = \
            self.redshift_backend.describe_tags_for_resource_type(resource_type)
        return self.get_response({
            "DescribeTagsResponse": {
                "DescribeTagsResult": {
                    "TaggedResources": tagged_resources
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })
