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
