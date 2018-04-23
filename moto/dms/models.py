from __future__ import unicode_literals
from datetime import datetime
# from datetime import timedelta
import uuid

import boto3
import pytz
# from dateutil.parser import parse as dtparse
from moto.core import BaseBackend, BaseModel
# from moto.dms.exceptions import DMSError
from .utils import (
    make_arn_for_endpoint,
    make_arn_for_replication_instance,
    make_arn_for_replication_task
)


class FakeReplicationInstance(BaseModel):

    def __init__(self, **kwargs):
        super(FakeReplicationInstance, self).__init__()
        self.replication_instance_identifier = kwargs['instance_id']
        self.replication_instance_class = kwargs['instance_class']
        self.dms_backend = kwargs['dms_backend']
        # self.region = kwargs['region']
        # self.region_id = kwargs['region_id']
        self.creation_datetime = datetime.now(pytz.utc)
        self.allocated_storage = kwargs.get('allocated_storage', 123)
        self.uuid = uuid.uuid4()

    @property
    def arn(self):
        return make_arn_for_replication_instance(self.dms_backend.region, self.dms_backend.region_id, self.uuid)


class FakeEndpoint(BaseModel):
    """docstring for FakeReplicationTask."""
    def __init__(self, **kwargs):
        super(FakeEndpoint, self).__init__()
        self.endpoint_identifier = kwargs['endpoint_id']
        self.endpoint_type = kwargs['endpoint_type']
        self.engine_name = kwargs['engine_name']
        self.dms_backend = kwargs['dms_backend']
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.server_name = kwargs.get('server_name')
        self.table_name = kwargs.get('table_name')
        self.port = kwargs.get('port')
        # self.region = kwargs['region']
        # self.region_id = kwargs['region_id']
        self.uuid = uuid.uuid4()

    @property
    def arn(self):
        return make_arn_for_endpoint(self.dms_backend.region, self.dms_backend.region_id, self.uuid)


class FakeReplicationTask(BaseModel):
    """docstring for FakeReplicationTask."""
    def __init__(self, **kwargs):
        super(FakeReplicationTask, self).__init__()
        self.replication_task_identifier = kwargs['task_id']
        self.replication_instance_arn = kwargs['instance_arn']
        self.source_endpoint_arn = kwargs['source_arn']
        self.target_endpoint_arn = kwargs['target_arn']
        self.migration_type = kwargs['migration_type']
        self.table_mappings = kwargs['table_mappings']
        self.dms_backend = kwargs['dms_backend']
        # self.region = kwargs['region']
        # self.region_id = kwargs['region_id']
        self.replication_task_settings = kwargs.get('task_settings', None)
        self.uuid = uuid.uuid4()
        self.creation_datetime = datetime.now(pytz.utc)
        self.start_datetime = None
        self.ready_datetime = None
        self.end_datetime = None
        self.state = 'creating'
        self.ready_task()

    @property
    def arn(self):
        return make_arn_for_replication_task(self.dms_backend.region, self.dms_backend.region_id, self.uuid)

    def ready_task(self):
        self.ready_datetime = datetime.now(pytz.utc)
        self.state = 'ready'

    def start_task(self):
        self.state = 'starting'
        self.start_datetime = datetime.now(pytz.utc)
        self.run_task()

    def run_task(self):
        self.state = 'running'

    def stop_task(self):
        self.state = 'stopped'
        self.end_datetime = datetime.now(pytz.utc)

    def delete_task(self):
        self.state = 'deleting'


class DatabaseMigrationServiceBackend(BaseBackend):

    def __init__(self, region_name):
        super(DatabaseMigrationServiceBackend, self).__init__()
        self.region_name = region_name
        self.region_id = uuid.uuid4()
        self.replication_tasks = {}
        self.replication_instances = {}
        self.endpoints = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_endpoint(self, endpoint_id, endpoint_type, engine_name):
        created_endpoint = FakeEndpoint(endpoint_id=endpoint_id, endpoint_type=endpoint_type, engine_name=engine_name, dms_backend=self)
        self.endpoints[created_endpoint.arn] = created_endpoint
        return created_endpoint

    def create_replication_task(self, **kwargs):
        # kwargs['region'] = self.region_name
        # kwargs['region_id'] = self.region_id
        kwargs['dms_backend'] = self
        created_replication_task = FakeReplicationTask(**kwargs)
        self.replication_tasks[created_replication_task.arn] = created_replication_task
        return created_replication_task

    def create_replication_instance(self, **kwargs):
        # kwargs['region'] = self.region_name
        # kwargs['region_id'] = self.region_id
        kwargs['dms_backend'] = self
        created_replication_instance = FakeReplicationInstance(**kwargs)
        self.replication_instances[created_replication_instance.arn] = created_replication_instance
        return created_replication_instance

    def delete_replication_task(self, task_arn):
        return self.replication_instances[task_arn].delete_task()

    def start_replication_task(self, task_arn):
        return self.replication_tasks[task_arn].start_task()

    def stop_replication_task(self, task_arn):
        return self.replication_tasks[task_arn].stop_task()

    def describe_replication_tasks(self, task_arn, marker=None):
        return self.replication_tasks[task_arn]

    def describe_replication_instances(self, instance_arn, marker=None):
        return self.replication_instances[instance_arn]

    def describe_endpoints(self, endpoint_arn, marker=None):
        return self.endpoints[endpoint_arn]
        # max_items = 50
        # groups = sorted(self.endpoints[endpoint_arn].instance_groups,
        #                 key=lambda x: x.id)
        # start_idx = 0 if marker is None else int(marker)
        # marker = None if len(groups) <= start_idx + \
        #     max_items else str(start_idx + max_items)
        # return groups[start_idx:start_idx + max_items], marker

    # def add_applications(self, cluster_id, applications):
    #     cluster = self.get_cluster(cluster_id)
    #     cluster.add_applications(applications)
    #
    # def add_instance_groups(self, cluster_id, instance_groups):
    #     cluster = self.clusters[cluster_id]
    #     result_groups = []
    #     for instance_group in instance_groups:
    #         group = FakeInstanceGroup(**instance_group)
    #         self.instance_groups[group.id] = group
    #         cluster.add_instance_group(group)
    #         result_groups.append(group)
    #     return result_groups
    #
    # def add_job_flow_steps(self, job_flow_id, steps):
    #     cluster = self.clusters[job_flow_id]
    #     steps = cluster.add_steps(steps)
    #     return steps
    #
    # def add_tags(self, cluster_id, tags):
    #     cluster = self.get_cluster(cluster_id)
    #     cluster.add_tags(tags)
    #
    # def describe_job_flows(self, job_flow_ids=None, job_flow_states=None, created_after=None, created_before=None):
    #     clusters = self.clusters.values()
    #
    #     within_two_month = datetime.now(pytz.utc) - timedelta(days=60)
    #     clusters = [
    #         c for c in clusters if c.creation_datetime >= within_two_month]
    #
    #     if job_flow_ids:
    #         clusters = [c for c in clusters if c.id in job_flow_ids]
    #     if job_flow_states:
    #         clusters = [c for c in clusters if c.state in job_flow_states]
    #     if created_after:
    #         created_after = dtparse(created_after)
    #         clusters = [
    #             c for c in clusters if c.creation_datetime > created_after]
    #     if created_before:
    #         created_before = dtparse(created_before)
    #         clusters = [
    #             c for c in clusters if c.creation_datetime < created_before]
    #
    #     # Amazon EMR can return a maximum of 512 job flow descriptions
    #     return sorted(clusters, key=lambda x: x.id)[:512]
    #
    # def describe_step(self, cluster_id, step_id):
    #     cluster = self.clusters[cluster_id]
    #     for step in cluster.steps:
    #         if step.id == step_id:
    #             return step
    #
    # def get_cluster(self, cluster_id):
    #     if cluster_id in self.clusters:
    #         return self.clusters[cluster_id]
    #     raise EmrError('ResourceNotFoundException', '', 'error_json')
    #
    # def get_instance_groups(self, instance_group_ids):
    #     return [
    #         group for group_id, group
    #         in self.instance_groups.items()
    #         if group_id in instance_group_ids
    #     ]
    #
    # def list_bootstrap_actions(self, cluster_id, marker=None):
    #     max_items = 50
    #     actions = self.clusters[cluster_id].bootstrap_actions
    #     start_idx = 0 if marker is None else int(marker)
    #     marker = None if len(actions) <= start_idx + \
    #         max_items else str(start_idx + max_items)
    #     return actions[start_idx:start_idx + max_items], marker
    #
    # def list_clusters(self, cluster_states=None, created_after=None,
    #                   created_before=None, marker=None):
    #     max_items = 50
    #     clusters = self.clusters.values()
    #     if cluster_states:
    #         clusters = [c for c in clusters if c.state in cluster_states]
    #     if created_after:
    #         created_after = dtparse(created_after)
    #         clusters = [
    #             c for c in clusters if c.creation_datetime > created_after]
    #     if created_before:
    #         created_before = dtparse(created_before)
    #         clusters = [
    #             c for c in clusters if c.creation_datetime < created_before]
    #     clusters = sorted(clusters, key=lambda x: x.id)
    #     start_idx = 0 if marker is None else int(marker)
    #     marker = None if len(clusters) <= start_idx + \
    #         max_items else str(start_idx + max_items)
    #     return clusters[start_idx:start_idx + max_items], marker
    #
    # def list_instance_groups(self, cluster_id, marker=None):
    #     max_items = 50
    #     groups = sorted(self.clusters[cluster_id].instance_groups,
    #                     key=lambda x: x.id)
    #     start_idx = 0 if marker is None else int(marker)
    #     marker = None if len(groups) <= start_idx + \
    #         max_items else str(start_idx + max_items)
    #     return groups[start_idx:start_idx + max_items], marker
    #
    # def list_steps(self, cluster_id, marker=None, step_ids=None, step_states=None):
    #     max_items = 50
    #     steps = self.clusters[cluster_id].steps
    #     if step_ids:
    #         steps = [s for s in steps if s.id in step_ids]
    #     if step_states:
    #         steps = [s for s in steps if s.state in step_states]
    #     start_idx = 0 if marker is None else int(marker)
    #     marker = None if len(steps) <= start_idx + \
    #         max_items else str(start_idx + max_items)
    #     return steps[start_idx:start_idx + max_items], marker
    #
    # def modify_instance_groups(self, instance_groups):
    #     result_groups = []
    #     for instance_group in instance_groups:
    #         group = self.instance_groups[instance_group['instance_group_id']]
    #         group.set_instance_count(int(instance_group['instance_count']))
    #     return result_groups
    #
    # def remove_tags(self, cluster_id, tag_keys):
    #     cluster = self.get_cluster(cluster_id)
    #     cluster.remove_tags(tag_keys)
    #
    # def run_job_flow(self, **kwargs):
    #     return FakeCluster(self, **kwargs)
    #
    # def set_visible_to_all_users(self, job_flow_ids, visible_to_all_users):
    #     for job_flow_id in job_flow_ids:
    #         cluster = self.clusters[job_flow_id]
    #         cluster.set_visibility(visible_to_all_users)
    #
    # def set_termination_protection(self, job_flow_ids, value):
    #     for job_flow_id in job_flow_ids:
    #         cluster = self.clusters[job_flow_id]
    #         cluster.set_termination_protection(value)
    #
    # def terminate_job_flows(self, job_flow_ids):
    #     clusters = []
    #     for job_flow_id in job_flow_ids:
    #         cluster = self.clusters[job_flow_id]
    #         cluster.terminate()
    #         clusters.append(cluster)
    #     return clusters


# dms_backends = {}
# for region in boto.dms.regions():
#     dms_backends[region.name] = DatabaseMigrationServiceBackend(region.name)
available_regions = boto3.session.Session().get_available_regions("dms")
dms_backends = {region: DatabaseMigrationServiceBackend(region_name=region) for region in available_regions}
