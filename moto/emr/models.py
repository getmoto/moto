from datetime import datetime
from datetime import timedelta

import warnings

import pytz
from boto3 import Session
from dateutil.parser import parse as dtparse
from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.emr.exceptions import (
    InvalidRequestException,
    ValidationException,
    ResourceNotFoundException,
)
from .utils import (
    random_instance_group_id,
    random_cluster_id,
    random_step_id,
    CamelToUnderscoresWalker,
    EmrSecurityGroupManager,
)

EXAMPLE_AMI_ID = "ami-12c6146b"


class FakeApplication(BaseModel):
    def __init__(self, name, version, args=None, additional_info=None):
        self.additional_info = additional_info or {}
        self.args = args or []
        self.name = name
        self.version = version


class FakeBootstrapAction(BaseModel):
    def __init__(self, args, name, script_path):
        self.args = args or []
        self.name = name
        self.script_path = script_path


class FakeInstance(BaseModel):
    def __init__(
        self, ec2_instance_id, instance_group, instance_fleet_id=None, id=None,
    ):
        self.id = id or random_instance_group_id()
        self.ec2_instance_id = ec2_instance_id
        self.instance_group = instance_group
        self.instance_fleet_id = instance_fleet_id


class FakeInstanceGroup(BaseModel):
    def __init__(
        self,
        cluster_id,
        instance_count,
        instance_role,
        instance_type,
        market="ON_DEMAND",
        name=None,
        id=None,
        bid_price=None,
        ebs_configuration=None,
        auto_scaling_policy=None,
    ):
        self.id = id or random_instance_group_id()
        self.cluster_id = cluster_id

        self.bid_price = bid_price
        self.market = market
        if name is None:
            if instance_role == "MASTER":
                name = "master"
            elif instance_role == "CORE":
                name = "slave"
            else:
                name = "Task instance group"
        self.name = name
        self.num_instances = instance_count
        self.role = instance_role
        self.type = instance_type
        self.ebs_configuration = ebs_configuration
        self.auto_scaling_policy = auto_scaling_policy
        self.creation_datetime = datetime.now(pytz.utc)
        self.start_datetime = datetime.now(pytz.utc)
        self.ready_datetime = datetime.now(pytz.utc)
        self.end_datetime = None
        self.state = "RUNNING"

    def set_instance_count(self, instance_count):
        self.num_instances = instance_count

    @property
    def auto_scaling_policy(self):
        return self._auto_scaling_policy

    @auto_scaling_policy.setter
    def auto_scaling_policy(self, value):
        if value is None:
            self._auto_scaling_policy = value
            return
        self._auto_scaling_policy = CamelToUnderscoresWalker.parse(value)
        self._auto_scaling_policy["status"] = {"state": "ATTACHED"}
        # Transform common ${emr.clusterId} placeholder in any dimensions it occurs in.
        if "rules" in self._auto_scaling_policy:
            for rule in self._auto_scaling_policy["rules"]:
                if (
                    "trigger" in rule
                    and "cloud_watch_alarm_definition" in rule["trigger"]
                    and "dimensions" in rule["trigger"]["cloud_watch_alarm_definition"]
                ):
                    for dimension in rule["trigger"]["cloud_watch_alarm_definition"][
                        "dimensions"
                    ]:
                        if (
                            "value" in dimension
                            and dimension["value"] == "${emr.clusterId}"
                        ):
                            dimension["value"] = self.cluster_id


class FakeStep(BaseModel):
    def __init__(
        self,
        state,
        name="",
        jar="",
        args=None,
        properties=None,
        action_on_failure="TERMINATE_CLUSTER",
    ):
        self.id = random_step_id()

        self.action_on_failure = action_on_failure
        self.args = args or []
        self.name = name
        self.jar = jar
        self.properties = properties or {}

        self.creation_datetime = datetime.now(pytz.utc)
        self.end_datetime = None
        self.ready_datetime = None
        self.start_datetime = None
        self.state = state

    def start(self):
        self.start_datetime = datetime.now(pytz.utc)


class FakeCluster(BaseModel):
    def __init__(
        self,
        emr_backend,
        name,
        log_uri,
        job_flow_role,
        service_role,
        steps,
        instance_attrs,
        bootstrap_actions=None,
        configurations=None,
        cluster_id=None,
        visible_to_all_users="false",
        release_label=None,
        requested_ami_version=None,
        running_ami_version=None,
        custom_ami_id=None,
        step_concurrency_level=1,
        security_configuration=None,
        kerberos_attributes=None,
        auto_scaling_role=None,
    ):
        self.id = cluster_id or random_cluster_id()
        emr_backend.clusters[self.id] = self
        self.emr_backend = emr_backend

        self.applications = []

        self.bootstrap_actions = []
        for bootstrap_action in bootstrap_actions or []:
            self.add_bootstrap_action(bootstrap_action)

        self.configurations = configurations or []

        self.tags = {}

        self.log_uri = log_uri
        self.name = name
        self.normalized_instance_hours = 0

        self.steps = []
        self.add_steps(steps)

        self.set_visibility(visible_to_all_users)

        self.instance_group_ids = []
        self.instances = []
        self.master_instance_group_id = None
        self.core_instance_group_id = None
        if (
            "master_instance_type" in instance_attrs
            and instance_attrs["master_instance_type"]
        ):
            self.emr_backend.add_instance_groups(
                self.id,
                [
                    {
                        "instance_count": 1,
                        "instance_role": "MASTER",
                        "instance_type": instance_attrs["master_instance_type"],
                        "market": "ON_DEMAND",
                        "name": "master",
                    }
                ],
            )
        if (
            "slave_instance_type" in instance_attrs
            and instance_attrs["slave_instance_type"]
        ):
            self.emr_backend.add_instance_groups(
                self.id,
                [
                    {
                        "instance_count": instance_attrs["instance_count"] - 1,
                        "instance_role": "CORE",
                        "instance_type": instance_attrs["slave_instance_type"],
                        "market": "ON_DEMAND",
                        "name": "slave",
                    }
                ],
            )
        self.additional_master_security_groups = instance_attrs.get(
            "additional_master_security_groups"
        )
        self.additional_slave_security_groups = instance_attrs.get(
            "additional_slave_security_groups"
        )
        self.availability_zone = instance_attrs.get("availability_zone")
        self.ec2_key_name = instance_attrs.get("ec2_key_name")
        self.ec2_subnet_id = instance_attrs.get("ec2_subnet_id")
        self.hadoop_version = instance_attrs.get("hadoop_version")
        self.keep_job_flow_alive_when_no_steps = instance_attrs.get(
            "keep_job_flow_alive_when_no_steps"
        )
        self.master_security_group = instance_attrs.get(
            "emr_managed_master_security_group"
        )
        self.service_access_security_group = instance_attrs.get(
            "service_access_security_group"
        )
        self.slave_security_group = instance_attrs.get(
            "emr_managed_slave_security_group"
        )
        self.termination_protected = instance_attrs.get("termination_protected")

        self.release_label = release_label
        self.requested_ami_version = requested_ami_version
        self.running_ami_version = running_ami_version
        self.custom_ami_id = custom_ami_id

        self.role = job_flow_role or "EMRJobflowDefault"
        self.service_role = service_role
        self.step_concurrency_level = step_concurrency_level

        self.creation_datetime = datetime.now(pytz.utc)
        self.start_datetime = None
        self.ready_datetime = None
        self.end_datetime = None
        self.state = None

        self.start_cluster()
        self.run_bootstrap_actions()
        if self.steps:
            self.steps[0].start()
        self.security_configuration = (
            security_configuration  # ToDo: Raise if doesn't already exist.
        )
        self.kerberos_attributes = kerberos_attributes
        self.auto_scaling_role = auto_scaling_role

    @property
    def arn(self):
        return "arn:aws:elasticmapreduce:{0}:{1}:cluster/{2}".format(
            self.emr_backend.region_name, ACCOUNT_ID, self.id
        )

    @property
    def instance_groups(self):
        return self.emr_backend.get_instance_groups(self.instance_group_ids)

    @property
    def master_instance_type(self):
        return self.emr_backend.instance_groups[self.master_instance_group_id].type

    @property
    def slave_instance_type(self):
        return self.emr_backend.instance_groups[self.core_instance_group_id].type

    @property
    def instance_count(self):
        return sum(group.num_instances for group in self.instance_groups)

    def start_cluster(self):
        self.state = "STARTING"
        self.start_datetime = datetime.now(pytz.utc)

    def run_bootstrap_actions(self):
        self.state = "BOOTSTRAPPING"
        self.ready_datetime = datetime.now(pytz.utc)
        self.state = "WAITING"
        if not self.steps:
            if not self.keep_job_flow_alive_when_no_steps:
                self.terminate()

    def terminate(self):
        self.state = "TERMINATING"
        self.end_datetime = datetime.now(pytz.utc)
        self.state = "TERMINATED"

    def add_applications(self, applications):
        self.applications.extend(
            [
                FakeApplication(
                    name=app.get("name", ""),
                    version=app.get("version", ""),
                    args=app.get("args", []),
                    additional_info=app.get("additiona_info", {}),
                )
                for app in applications
            ]
        )

    def add_bootstrap_action(self, bootstrap_action):
        self.bootstrap_actions.append(FakeBootstrapAction(**bootstrap_action))

    def add_instance_group(self, instance_group):
        if instance_group.role == "MASTER":
            if self.master_instance_group_id:
                raise Exception("Cannot add another master instance group")
            self.master_instance_group_id = instance_group.id
            num_master_nodes = instance_group.num_instances
            if num_master_nodes > 1:
                # Cluster is HA
                if num_master_nodes != 3:
                    raise ValidationException(
                        "Master instance group must have exactly 3 instances for HA clusters."
                    )
                self.keep_job_flow_alive_when_no_steps = True
                self.termination_protected = True
        if instance_group.role == "CORE":
            if self.core_instance_group_id:
                raise Exception("Cannot add another core instance group")
            self.core_instance_group_id = instance_group.id
        self.instance_group_ids.append(instance_group.id)

    def add_instance(self, instance):
        self.instances.append(instance)

    def add_steps(self, steps):
        added_steps = []
        for step in steps:
            if self.steps:
                # If we already have other steps, this one is pending
                fake = FakeStep(state="PENDING", **step)
            else:
                fake = FakeStep(state="RUNNING", **step)
            self.steps.append(fake)
            added_steps.append(fake)
        self.state = "RUNNING"
        return added_steps

    def add_tags(self, tags):
        self.tags.update(tags)

    def remove_tags(self, tag_keys):
        for key in tag_keys:
            self.tags.pop(key, None)

    def set_termination_protection(self, value):
        self.termination_protected = value

    def set_visibility(self, visibility):
        self.visible_to_all_users = visibility


class FakeSecurityConfiguration(BaseModel):
    def __init__(self, name, security_configuration):
        self.name = name
        self.security_configuration = security_configuration
        self.creation_date_time = datetime.now(pytz.utc)


class ElasticMapReduceBackend(BaseBackend):
    def __init__(self, region_name):
        super(ElasticMapReduceBackend, self).__init__()
        self.region_name = region_name
        self.clusters = {}
        self.instance_groups = {}
        self.security_configurations = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "elasticmapreduce"
        )

    @property
    def ec2_backend(self):
        """
        :return: EC2 Backend
        :rtype: moto.ec2.models.EC2Backend
        """
        from moto.ec2 import ec2_backends

        return ec2_backends[self.region_name]

    def add_applications(self, cluster_id, applications):
        cluster = self.describe_cluster(cluster_id)
        cluster.add_applications(applications)

    def add_instance_groups(self, cluster_id, instance_groups):
        cluster = self.clusters[cluster_id]
        result_groups = []
        for instance_group in instance_groups:
            group = FakeInstanceGroup(cluster_id=cluster_id, **instance_group)
            self.instance_groups[group.id] = group
            cluster.add_instance_group(group)
            result_groups.append(group)
        return result_groups

    def add_instances(self, cluster_id, instances, instance_group):
        cluster = self.clusters[cluster_id]
        response = self.ec2_backend.add_instances(
            EXAMPLE_AMI_ID, instances["instance_count"], "", [], **instances
        )
        for instance in response.instances:
            instance = FakeInstance(
                ec2_instance_id=instance.id, instance_group=instance_group,
            )
            cluster.add_instance(instance)

    def add_job_flow_steps(self, job_flow_id, steps):
        cluster = self.clusters[job_flow_id]
        steps = cluster.add_steps(steps)
        return steps

    def add_tags(self, cluster_id, tags):
        cluster = self.describe_cluster(cluster_id)
        cluster.add_tags(tags)

    def describe_job_flows(
        self,
        job_flow_ids=None,
        job_flow_states=None,
        created_after=None,
        created_before=None,
    ):
        clusters = self.clusters.values()

        within_two_month = datetime.now(pytz.utc) - timedelta(days=60)
        clusters = [c for c in clusters if c.creation_datetime >= within_two_month]

        if job_flow_ids:
            clusters = [c for c in clusters if c.id in job_flow_ids]
        if job_flow_states:
            clusters = [c for c in clusters if c.state in job_flow_states]
        if created_after:
            created_after = dtparse(created_after)
            clusters = [c for c in clusters if c.creation_datetime > created_after]
        if created_before:
            created_before = dtparse(created_before)
            clusters = [c for c in clusters if c.creation_datetime < created_before]

        # Amazon EMR can return a maximum of 512 job flow descriptions
        return sorted(clusters, key=lambda x: x.id)[:512]

    def describe_step(self, cluster_id, step_id):
        cluster = self.clusters[cluster_id]
        for step in cluster.steps:
            if step.id == step_id:
                return step

    def describe_cluster(self, cluster_id):
        if cluster_id in self.clusters:
            return self.clusters[cluster_id]
        raise ResourceNotFoundException("")

    def get_instance_groups(self, instance_group_ids):
        return [
            group
            for group_id, group in self.instance_groups.items()
            if group_id in instance_group_ids
        ]

    def list_bootstrap_actions(self, cluster_id, marker=None):
        max_items = 50
        actions = self.clusters[cluster_id].bootstrap_actions
        start_idx = 0 if marker is None else int(marker)
        marker = (
            None
            if len(actions) <= start_idx + max_items
            else str(start_idx + max_items)
        )
        return actions[start_idx : start_idx + max_items], marker

    def list_clusters(
        self, cluster_states=None, created_after=None, created_before=None, marker=None
    ):
        max_items = 50
        clusters = self.clusters.values()
        if cluster_states:
            clusters = [c for c in clusters if c.state in cluster_states]
        if created_after:
            created_after = dtparse(created_after)
            clusters = [c for c in clusters if c.creation_datetime > created_after]
        if created_before:
            created_before = dtparse(created_before)
            clusters = [c for c in clusters if c.creation_datetime < created_before]
        clusters = sorted(clusters, key=lambda x: x.id)
        start_idx = 0 if marker is None else int(marker)
        marker = (
            None
            if len(clusters) <= start_idx + max_items
            else str(start_idx + max_items)
        )
        return clusters[start_idx : start_idx + max_items], marker

    def list_instance_groups(self, cluster_id, marker=None):
        max_items = 50
        groups = sorted(self.clusters[cluster_id].instance_groups, key=lambda x: x.id)
        start_idx = 0 if marker is None else int(marker)
        marker = (
            None if len(groups) <= start_idx + max_items else str(start_idx + max_items)
        )
        return groups[start_idx : start_idx + max_items], marker

    def list_instances(
        self, cluster_id, marker=None, instance_group_id=None, instance_group_types=None
    ):
        max_items = 50
        groups = sorted(self.clusters[cluster_id].instances, key=lambda x: x.id)
        start_idx = 0 if marker is None else int(marker)
        marker = (
            None if len(groups) <= start_idx + max_items else str(start_idx + max_items)
        )
        if instance_group_id:
            groups = [g for g in groups if g.instance_group.id == instance_group_id]
        if instance_group_types:
            groups = [
                g for g in groups if g.instance_group.role in instance_group_types
            ]
        for g in groups:
            g.details = self.ec2_backend.get_instance(g.ec2_instance_id)
        return groups[start_idx : start_idx + max_items], marker

    def list_steps(self, cluster_id, marker=None, step_ids=None, step_states=None):
        max_items = 50
        steps = self.clusters[cluster_id].steps
        if step_ids:
            steps = [s for s in steps if s.id in step_ids]
        if step_states:
            steps = [s for s in steps if s.state in step_states]
        start_idx = 0 if marker is None else int(marker)
        marker = (
            None if len(steps) <= start_idx + max_items else str(start_idx + max_items)
        )
        return steps[start_idx : start_idx + max_items], marker

    def modify_cluster(self, cluster_id, step_concurrency_level):
        cluster = self.clusters[cluster_id]
        cluster.step_concurrency_level = step_concurrency_level
        return cluster

    def modify_instance_groups(self, instance_groups):
        result_groups = []
        for instance_group in instance_groups:
            group = self.instance_groups[instance_group["instance_group_id"]]
            group.set_instance_count(int(instance_group["instance_count"]))
        return result_groups

    def remove_tags(self, cluster_id, tag_keys):
        cluster = self.describe_cluster(cluster_id)
        cluster.remove_tags(tag_keys)

    def _manage_security_groups(
        self,
        ec2_subnet_id,
        emr_managed_master_security_group,
        emr_managed_slave_security_group,
        service_access_security_group,
        **_
    ):
        default_return_value = (
            emr_managed_master_security_group,
            emr_managed_slave_security_group,
            service_access_security_group,
        )
        if not ec2_subnet_id:
            # TODO: Set up Security Groups in Default VPC.
            return default_return_value

        from moto.ec2.exceptions import InvalidSubnetIdError

        try:
            subnet = self.ec2_backend.get_subnet(ec2_subnet_id)
        except InvalidSubnetIdError:
            warnings.warn(
                "Could not find Subnet with id: {0}\n"
                "In the near future, this will raise an error.\n"
                "Use ec2.describe_subnets() to find a suitable id "
                "for your test.".format(ec2_subnet_id),
                PendingDeprecationWarning,
            )
            return default_return_value

        manager = EmrSecurityGroupManager(self.ec2_backend, subnet.vpc_id)
        master, slave, service = manager.manage_security_groups(
            emr_managed_master_security_group,
            emr_managed_slave_security_group,
            service_access_security_group,
        )
        return master.id, slave.id, service.id

    def run_job_flow(self, **kwargs):
        (
            kwargs["instance_attrs"]["emr_managed_master_security_group"],
            kwargs["instance_attrs"]["emr_managed_slave_security_group"],
            kwargs["instance_attrs"]["service_access_security_group"],
        ) = self._manage_security_groups(**kwargs["instance_attrs"])
        return FakeCluster(self, **kwargs)

    def set_visible_to_all_users(self, job_flow_ids, visible_to_all_users):
        for job_flow_id in job_flow_ids:
            cluster = self.clusters[job_flow_id]
            cluster.set_visibility(visible_to_all_users)

    def set_termination_protection(self, job_flow_ids, value):
        for job_flow_id in job_flow_ids:
            cluster = self.clusters[job_flow_id]
            cluster.set_termination_protection(value)

    def terminate_job_flows(self, job_flow_ids):
        clusters_terminated = []
        clusters_protected = []
        for job_flow_id in job_flow_ids:
            cluster = self.clusters[job_flow_id]
            if cluster.termination_protected:
                clusters_protected.append(cluster)
                continue
            cluster.terminate()
            clusters_terminated.append(cluster)
        if clusters_protected:
            raise ValidationException(
                "Could not shut down one or more job flows since they are termination protected."
            )
        return clusters_terminated

    def put_auto_scaling_policy(self, instance_group_id, auto_scaling_policy):
        instance_groups = self.get_instance_groups(
            instance_group_ids=[instance_group_id]
        )
        if len(instance_groups) == 0:
            return None
        instance_group = instance_groups[0]
        instance_group.auto_scaling_policy = auto_scaling_policy
        return instance_group

    def remove_auto_scaling_policy(self, cluster_id, instance_group_id):
        instance_groups = self.get_instance_groups(
            instance_group_ids=[instance_group_id]
        )
        if len(instance_groups) == 0:
            return None
        instance_group = instance_groups[0]
        instance_group.auto_scaling_policy = None

    def create_security_configuration(self, name, security_configuration):
        if name in self.security_configurations:
            raise InvalidRequestException(
                message="SecurityConfiguration with name '{}' already exists.".format(
                    name
                )
            )
        security_configuration = FakeSecurityConfiguration(
            name=name, security_configuration=security_configuration
        )
        self.security_configurations[name] = security_configuration
        return security_configuration

    def get_security_configuration(self, name):
        if name not in self.security_configurations:
            raise InvalidRequestException(
                message="Security configuration with name '{}' does not exist.".format(
                    name
                )
            )
        return self.security_configurations[name]

    def delete_security_configuration(self, name):
        if name not in self.security_configurations:
            raise InvalidRequestException(
                message="Security configuration with name '{}' does not exist.".format(
                    name
                )
            )
        del self.security_configurations[name]


emr_backends = {}
for region in Session().get_available_regions("emr"):
    emr_backends[region] = ElasticMapReduceBackend(region)
for region in Session().get_available_regions("emr", partition_name="aws-us-gov"):
    emr_backends[region] = ElasticMapReduceBackend(region)
for region in Session().get_available_regions("emr", partition_name="aws-cn"):
    emr_backends[region] = ElasticMapReduceBackend(region)
