from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class RedshiftClientError(BadRequest):

    def __init__(self, code, message):
        super(RedshiftClientError, self).__init__()
        self.description = json.dumps({
            "Error": {
                "Code": code,
                "Message": message,
                'Type': 'Sender',
            },
            'RequestId': '6876f774-7273-11e4-85dc-39e55ca848d1',
        })


class ClusterNotFoundError(RedshiftClientError):

    def __init__(self, cluster_identifier):
        super(ClusterNotFoundError, self).__init__(
            'ClusterNotFound',
            "Cluster {0} not found.".format(cluster_identifier))


class ClusterSubnetGroupNotFoundError(RedshiftClientError):

    def __init__(self, subnet_identifier):
        super(ClusterSubnetGroupNotFoundError, self).__init__(
            'ClusterSubnetGroupNotFound',
            "Subnet group {0} not found.".format(subnet_identifier))


class ClusterSecurityGroupNotFoundError(RedshiftClientError):

    def __init__(self, group_identifier):
        super(ClusterSecurityGroupNotFoundError, self).__init__(
            'ClusterSecurityGroupNotFound',
            "Security group {0} not found.".format(group_identifier))


class ClusterParameterGroupNotFoundError(RedshiftClientError):

    def __init__(self, group_identifier):
        super(ClusterParameterGroupNotFoundError, self).__init__(
            'ClusterParameterGroupNotFound',
            "Parameter group {0} not found.".format(group_identifier))


class InvalidSubnetError(RedshiftClientError):

    def __init__(self, subnet_identifier):
        super(InvalidSubnetError, self).__init__(
            'InvalidSubnet',
            "Subnet {0} not found.".format(subnet_identifier))
