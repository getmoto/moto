from __future__ import unicode_literals
import re
# import uuid

# uuid.uuid4()

# source_endpoint_arn='arn:aws:dms:us-west-2:616371729415:endpoint:PD52Q3DHL56LXS2SK5UA5I5LJI',
#     target_endpoint_arn='arn:aws:dms:us-west-2:616371729415:endpoint:3QOWZ7XQVMZRGCIGUWRAVBQ6MU',
    # replication_instance_arn='arn:aws:dms:us-west-2:616371729415:rep:TEWGIDVJINDWEFSIGBP6IBLYFM',
# Running create DMS Task with arn: arn:aws:dms:us-west-2:616371729415:task:AZPLHUYLSYJDEUOCUOMHDJMUOQ

def make_replication_arn(region_name, region_id, custom_type, custom_type_id):
    return "arn:aws:dms:{0}:{1}:{2}:{3}".format(region_name, region_id, custom_type, custom_type_id)

def make_arn_for_endpoint(region_name, region_id, endpoint_id):
    return make_replication_arn(region_name, region_id, 'endpoint', endpoint_id)

def make_arn_for_replication_instance(region_name, region_id, instance_id):
    return make_replication_arn(region_name, region_id, 'rep', instance_id)

def make_arn_for_replication_task(region_name, region_id, task_id):
    return make_replication_arn(region_name, region_id, 'task', task_id)
