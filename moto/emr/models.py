from __future__ import unicode_literals

import boto.emr
from moto.core import BaseBackend

from .utils import random_instance_group_id, random_job_id

DEFAULT_JOB_FLOW_ROLE = 'EMRJobflowDefault'


class FakeInstanceGroup(object):
    def __init__(self, id, instance_count, instance_role, instance_type, market, name, bid_price=None):
        self.id = id
        self.num_instances = instance_count
        self.role = instance_role
        self.type = instance_type
        self.market = market
        self.name = name
        self.bid_price = bid_price

    def set_instance_count(self, instance_count):
        self.num_instances = instance_count


class Cluster(object):
    def __init__(self, id, name, availability_zone, ec2_key_name, subnet_id,
            ec2_iam_profile, log_uri):
        self.id = id
        self.name = name
        self.applications = []
        self.auto_terminate = "false"
        self.availability_zone = availability_zone
        self.subnet_id = subnet_id
        self.ec2_iam_profile = ec2_iam_profile
        self.log_uri = log_uri
        self.master_public_dns_name = ""
        self.normalized_instance_hours = 0
        self.requested_ami_version = "2.4.2"
        self.running_ami_version = "2.4.2"
        self.service_role = "my-service-role"
        self.state = "RUNNING"
        self.tags = {}
        self.termination_protected = "false"
        self.visible_to_all_users = "false"

    def add_tags(self, tags):
        self.tags.update(tags)

    def remove_tags(self, tag_keys):
        for key in tag_keys:
            self.tags.pop(key, None)


class FakeStep(object):
    def __init__(self, state, **kwargs):
        # 'Steps.member.1.HadoopJarStep.Jar': ['/home/hadoop/contrib/streaming/hadoop-streaming.jar'],
        # 'Steps.member.1.HadoopJarStep.Args.member.1': ['-mapper'],
        # 'Steps.member.1.HadoopJarStep.Args.member.2': ['s3n://elasticmapreduce/samples/wordcount/wordSplitter.py'],
        # 'Steps.member.1.HadoopJarStep.Args.member.3': ['-reducer'],
        # 'Steps.member.1.HadoopJarStep.Args.member.4': ['aggregate'],
        # 'Steps.member.1.HadoopJarStep.Args.member.5': ['-input'],
        # 'Steps.member.1.HadoopJarStep.Args.member.6': ['s3n://elasticmapreduce/samples/wordcount/input'],
        # 'Steps.member.1.HadoopJarStep.Args.member.7': ['-output'],
        # 'Steps.member.1.HadoopJarStep.Args.member.8': ['s3n://<my output bucket>/output/wordcount_output'],
        # 'Steps.member.1.ActionOnFailure': ['TERMINATE_JOB_FLOW'],
        # 'Steps.member.1.Name': ['My wordcount example']}

        self.action_on_failure = kwargs['action_on_failure']
        self.name = kwargs['name']
        self.jar = kwargs['hadoop_jar_step._jar']
        self.args = []
        self.state = state

        arg_index = 1
        while True:
            arg = kwargs.get('hadoop_jar_step._args.member.{0}'.format(arg_index))
            if arg:
                self.args.append(arg)
                arg_index += 1
            else:
                break


class FakeJobFlow(object):
    def __init__(self, job_id, name, log_uri, job_flow_role, visible_to_all_users, steps, instance_attrs, emr_backend):
        self.id = job_id
        self.name = name
        self.log_uri = log_uri
        self.role = job_flow_role or DEFAULT_JOB_FLOW_ROLE
        self.state = "STARTING"
        self.steps = []
        self.add_steps(steps)

        self.initial_instance_count = instance_attrs.get('instance_count', 0)
        self.initial_master_instance_type = instance_attrs.get('master_instance_type')
        self.initial_slave_instance_type = instance_attrs.get('slave_instance_type')

        self.set_visibility(visible_to_all_users)
        self.normalized_instance_hours = 0
        self.ec2_key_name = instance_attrs.get('ec2_key_name')
        self.availability_zone = instance_attrs.get('placement.availability_zone')
        self.subnet_id = instance_attrs.get('ec2_subnet_id')
        self.keep_job_flow_alive_when_no_steps = instance_attrs.get('keep_job_flow_alive_when_no_steps')
        self.termination_protected = instance_attrs.get('termination_protected')

        self.instance_group_ids = []

        self.emr_backend = emr_backend

    def create_cluster(self):
        cluster = Cluster(
            id=self.id,
            name=self.name,
            availability_zone=self.availability_zone,
            ec2_key_name=self.ec2_key_name,
            subnet_id=self.subnet_id,
            ec2_iam_profile=self.role,
            log_uri=self.log_uri,
        )
        return cluster

    def terminate(self):
        self.state = 'TERMINATED'

    def set_visibility(self, visibility):
        if visibility == 'true':
            self.visible_to_all_users = True
        else:
            self.visible_to_all_users = False

    def set_termination_protection(self, value):
        self.termination_protected = value

    def add_steps(self, steps):
        for index, step in enumerate(steps):
            if self.steps:
                # If we already have other steps, this one is pending
                self.steps.append(FakeStep(state='PENDING', **step))
            else:
                self.steps.append(FakeStep(state='STARTING', **step))

    def add_instance_group(self, instance_group_id):
        self.instance_group_ids.append(instance_group_id)

    @property
    def instance_groups(self):
        return self.emr_backend.get_instance_groups(self.instance_group_ids)

    @property
    def master_instance_type(self):
        groups = self.instance_groups
        if groups:
            return groups[0].type
        else:
            return self.initial_master_instance_type

    @property
    def slave_instance_type(self):
        groups = self.instance_groups
        if groups:
            return groups[0].type
        else:
            return self.initial_slave_instance_type

    @property
    def instance_count(self):
        groups = self.instance_groups
        if not groups:
            # No groups,return initial instance count
            return self.initial_instance_count
        count = 0
        for group in groups:
            count += int(group.num_instances)
        return count


class ElasticMapReduceBackend(BaseBackend):

    def __init__(self):
        self.job_flows = {}
        self.clusters = {}
        self.instance_groups = {}

    def run_job_flow(self, name, log_uri, job_flow_role, visible_to_all_users, steps, instance_attrs):
        job_id = random_job_id()
        job_flow = FakeJobFlow(
            job_id, name, log_uri, job_flow_role, visible_to_all_users, steps, instance_attrs, self)
        self.job_flows[job_id] = job_flow
        cluster = job_flow.create_cluster()
        self.clusters[cluster.id] = cluster
        return job_flow

    def add_job_flow_steps(self, job_flow_id, steps):
        job_flow = self.job_flows[job_flow_id]
        job_flow.add_steps(steps)
        return job_flow

    def describe_job_flows(self, job_flow_ids=None):
        jobs = self.job_flows.values()
        if job_flow_ids:
            return [job for job in jobs if job.id in job_flow_ids]
        else:
            return jobs

    def terminate_job_flows(self, job_ids):
        flows = [flow for flow in self.describe_job_flows() if flow.id in job_ids]
        for flow in flows:
            flow.terminate()
        return flows

    def list_clusters(self):
        return self.clusters.values()

    def get_cluster(self, cluster_id):
        return self.clusters[cluster_id]

    def get_instance_groups(self, instance_group_ids):
        return [
            group for group_id, group
            in self.instance_groups.items()
            if group_id in instance_group_ids
        ]

    def add_instance_groups(self, job_flow_id, instance_groups):
        job_flow = self.job_flows[job_flow_id]
        result_groups = []
        for instance_group in instance_groups:
            instance_group_id = random_instance_group_id()
            group = FakeInstanceGroup(instance_group_id, **instance_group)
            self.instance_groups[instance_group_id] = group
            job_flow.add_instance_group(instance_group_id)
            result_groups.append(group)
        return result_groups

    def modify_instance_groups(self, instance_groups):
        result_groups = []
        for instance_group in instance_groups:
            group = self.instance_groups[instance_group['instance_group_id']]
            group.set_instance_count(instance_group['instance_count'])
        return result_groups

    def set_visible_to_all_users(self, job_ids, visible_to_all_users):
        for job_id in job_ids:
            job = self.job_flows[job_id]
            job.set_visibility(visible_to_all_users)

    def set_termination_protection(self, job_ids, value):
        for job_id in job_ids:
            job = self.job_flows[job_id]
            job.set_termination_protection(value)

    def add_tags(self, cluster_id, tags):
        cluster = self.get_cluster(cluster_id)
        cluster.add_tags(tags)

    def remove_tags(self, cluster_id, tag_keys):
        cluster = self.get_cluster(cluster_id)
        cluster.remove_tags(tag_keys)


emr_backends = {}
for region in boto.emr.regions():
    emr_backends[region.name] = ElasticMapReduceBackend()
