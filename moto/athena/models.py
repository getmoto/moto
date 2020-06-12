from __future__ import unicode_literals
import time

from boto3 import Session
from moto.core import BaseBackend, BaseModel, ACCOUNT_ID

from uuid import uuid4


class TaggableResourceMixin(object):
    # This mixing was copied from Redshift when initially implementing
    # Athena. TBD if it's worth the overhead.

    def __init__(self, region_name, resource_name, tags):
        self.region = region_name
        self.resource_name = resource_name
        self.tags = tags or []

    @property
    def arn(self):
        return "arn:aws:athena:{region}:{account_id}:{resource_name}".format(
            region=self.region, account_id=ACCOUNT_ID, resource_name=self.resource_name
        )

    def create_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def delete_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]
        return self.tags


class WorkGroup(TaggableResourceMixin, BaseModel):

    resource_type = "workgroup"
    state = "ENABLED"

    def __init__(self, athena_backend, name, configuration, description, tags):
        self.region_name = athena_backend.region_name
        super(WorkGroup, self).__init__(
            self.region_name, "workgroup/{}".format(name), tags
        )
        self.athena_backend = athena_backend
        self.name = name
        self.description = description
        self.configuration = configuration


class Execution(BaseModel):
    def __init__(self, query, context, config, workgroup):
        self.id = str(uuid4())
        self.query = query
        self.context = context
        self.config = config
        self.workgroup = workgroup
        self.start_time = time.time()
        self.status = "QUEUED"


class AthenaBackend(BaseBackend):
    region_name = None

    def __init__(self, region_name=None):
        if region_name is not None:
            self.region_name = region_name
        self.work_groups = {}
        self.executions = {}

    def create_work_group(self, name, configuration, description, tags):
        if name in self.work_groups:
            return None
        work_group = WorkGroup(self, name, configuration, description, tags)
        self.work_groups[name] = work_group
        return work_group

    def list_work_groups(self):
        return [
            {
                "Name": wg.name,
                "State": wg.state,
                "Description": wg.description,
                "CreationTime": time.time(),
            }
            for wg in self.work_groups.values()
        ]

    def get_work_group(self, name):
        if name not in self.work_groups:
            return None
        wg = self.work_groups[name]
        return {
            "Name": wg.name,
            "State": wg.state,
            "Configuration": wg.configuration,
            "Description": wg.description,
            "CreationTime": time.time(),
        }

    def start_query_execution(self, query, context, config, workgroup):
        execution = Execution(
            query=query, context=context, config=config, workgroup=workgroup
        )
        self.executions[execution.id] = execution
        return execution.id

    def get_execution(self, exec_id):
        return self.executions[exec_id]

    def stop_query_execution(self, exec_id):
        execution = self.executions[exec_id]
        execution.status = "CANCELLED"


athena_backends = {}
for region in Session().get_available_regions("athena"):
    athena_backends[region] = AthenaBackend(region)
for region in Session().get_available_regions("athena", partition_name="aws-us-gov"):
    athena_backends[region] = AthenaBackend(region)
for region in Session().get_available_regions("athena", partition_name="aws-cn"):
    athena_backends[region] = AthenaBackend(region)
