from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class RDSClientError(BadRequest):

    def __init__(self, code, message):
        super(RDSClientError, self).__init__()
        self.description = json.dumps({
            "Error": {
                "Code": code,
                "Message": message,
                'Type': 'Sender',
            },
            'RequestId': '6876f774-7273-11e4-85dc-39e55ca848d1',
        })


class DBInstanceNotFoundError(RDSClientError):

    def __init__(self, database_identifier):
        super(DBInstanceNotFoundError, self).__init__(
            'DBInstanceNotFound',
            "Database {0} not found.".format(database_identifier))


class DBSecurityGroupNotFoundError(RDSClientError):

    def __init__(self, security_group_name):
        super(DBSecurityGroupNotFoundError, self).__init__(
            'DBSecurityGroupNotFound',
            "Security Group {0} not found.".format(security_group_name))


class DBSubnetGroupNotFoundError(RDSClientError):

    def __init__(self, subnet_group_name):
        super(DBSubnetGroupNotFoundError, self).__init__(
            'DBSubnetGroupNotFound',
            "Subnet Group {0} not found.".format(subnet_group_name))
