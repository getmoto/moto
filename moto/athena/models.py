from __future__ import unicode_literals
import time

from boto3 import Session

from moto.core import BaseBackend, BaseModel

from moto.core import ACCOUNT_ID


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


class AthenaBackend(BaseBackend):
    region_name = None

    def __init__(self, region_name=None):
        if region_name is not None:
            self.region_name = region_name
        self.work_groups = {}

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


athena_backends = {}
for region in Session().get_available_regions("athena"):
    athena_backends[region] = AthenaBackend(region)
for region in Session().get_available_regions("athena", partition_name="aws-us-gov"):
    athena_backends[region] = AthenaBackend(region)
for region in Session().get_available_regions("athena", partition_name="aws-cn"):
    athena_backends[region] = AthenaBackend(region)
