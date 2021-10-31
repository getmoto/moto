"""EMRContainersBackend class with methods for supported APIs."""
from datetime import datetime
from boto3 import Session

from moto.core import BaseBackend, BaseModel, ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds

from .utils import random_cluster_id, random_job_id, get_partition, paginated_list

# String Templates
from ..config.exceptions import ValidationException

VIRTUAL_CLUSTER_ARN_TEMPLATE = (
    "arn:{partition}:emr-containers:{region}:"
    + str(ACCOUNT_ID)
    + ":/virtualclusters/{virtual_cluster_id}"
)

JOB_ARN_TEMPLATE = (
    "arn:{partition}:emr-containers:{region}:"
    + str(ACCOUNT_ID)
    + ":/virtualclusters/{virtual_cluster_id}/jobruns/{job_id}"
)

# Defaults used for creating a Virtual cluster
VIRTUAL_CLUSTER_STATUS = "RUNNING"
JOB_STATUS = "RUNNING"


class FakeCluster(BaseModel):
    def __init__(
        self,
        name,
        container_provider,
        client_token,
        region_name,
        aws_partition,
        tags=None,
        virtual_cluster_id=None,
    ):
        self.id = virtual_cluster_id or random_cluster_id()

        self.name = name
        self.client_token = client_token
        self.arn = VIRTUAL_CLUSTER_ARN_TEMPLATE.format(
            partition=aws_partition, region=region_name, virtual_cluster_id=self.id
        )
        self.state = VIRTUAL_CLUSTER_STATUS
        self.container_provider = container_provider
        self.container_provider_id = container_provider["id"]
        self.namespace = container_provider["info"]["eksInfo"]["namespace"]
        self.creation_date = iso_8601_datetime_without_milliseconds(
            datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.tags = tags

    def __iter__(self):
        yield "id", self.id
        yield "name", self.name
        yield "arn", self.arn
        yield "state", self.state
        yield "containerProvider", self.container_provider
        yield "createdAt", self.creation_date
        yield "tags", self.tags

    def to_dict(self):
        # Format for summary https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_DescribeVirtualCluster.html
        # (response syntax section)
        return {
            "id": self.id,
            "name": self.name,
            "arn": self.arn,
            "state": self.state,
            "containerProvider": self.container_provider,
            "createdAt": self.creation_date,
            "tags": self.tags,
        }


class FakeJob(BaseModel):
    def __init__(
        self,
        name,
        virtual_cluster_id,
        client_token,
        execution_role_arn,
        release_label,
        job_driver,
        configuration_overrides,
        region_name,
        aws_partition,
        tags,
    ):
        self.id = random_job_id()
        self.name = name
        self.virtual_cluster_id = virtual_cluster_id
        self.arn = JOB_ARN_TEMPLATE.format(
            partition=aws_partition,
            region=region_name,
            virtual_cluster_id=self.virtual_cluster_id,
            job_id=self.id,
        )
        self.state = JOB_STATUS
        self.client_token = client_token
        self.execution_role_arn = execution_role_arn
        self.release_label = release_label
        self.job_driver = job_driver
        self.configuration_overrides = configuration_overrides
        self.created_at = iso_8601_datetime_without_milliseconds(
            datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.created_by = None
        self.finished_at = None
        self.state_details = None
        self.failure_reason = None
        self.tags = tags

    def __iter__(self):
        yield "id", self.id
        yield "name", self.name
        yield "virtualClusterId", self.virtual_cluster_id
        yield "arn", self.arn
        yield "state", self.state
        yield "clientToken", self.client_token
        yield "executionRoleArn", self.execution_role_arn
        yield "releaseLabel", self.release_label
        yield "configurationOverrides", self.release_label
        yield "jobDriver", self.job_driver
        yield "createdAt", self.created_at
        yield "createdBy", self.created_by
        yield "finishedAt", self.finished_at
        yield "stateDetails", self.state_details
        yield "failureReason", self.failure_reason
        yield "tags", self.tags


class EMRContainersBackend(BaseBackend):
    """Implementation of EMRContainers APIs."""

    def __init__(self, region_name=None):
        super(EMRContainersBackend, self).__init__()
        self.virtual_clusters = dict()
        self.virtual_cluster_count = 0
        self.jobs = dict()
        self.job_count = 0
        self.region_name = region_name
        self.partition = get_partition(region_name)

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_virtual_cluster(self, name, container_provider, client_token, tags=None):
        occupied_namespaces = [
            virtual_cluster.namespace
            for virtual_cluster in self.virtual_clusters.values()
        ]

        if container_provider["info"]["eksInfo"]["namespace"] in occupied_namespaces:
            raise ValidationException(
                "A virtual cluster already exists in the given namespace"
            )

        virtual_cluster = FakeCluster(
            name=name,
            container_provider=container_provider,
            client_token=client_token,
            tags=tags,
            region_name=self.region_name,
            aws_partition=self.partition,
        )

        self.virtual_clusters[virtual_cluster.id] = virtual_cluster
        self.virtual_cluster_count += 1
        return virtual_cluster

    def delete_virtual_cluster(self, id):
        if id not in self.virtual_clusters:
            raise ValidationException("VirtualCluster does not exist")

        self.virtual_clusters[id].state = "TERMINATED"
        return self.virtual_clusters[id]

    def describe_virtual_cluster(self, id):
        if id not in self.virtual_clusters:
            raise ValidationException(f"Virtual cluster {id} doesn't exist.")

        return self.virtual_clusters[id].to_dict()

    def list_virtual_clusters(
        self,
        container_provider_id,
        container_provider_type,
        created_after,
        created_before,
        states,
        max_results,
        next_token,
    ):
        virtual_clusters = [
            virtual_cluster.to_dict()
            for virtual_cluster in self.virtual_clusters.values()
        ]

        if container_provider_id:
            virtual_clusters = [
                virtual_cluster
                for virtual_cluster in virtual_clusters
                if virtual_cluster["containerProvider"]["id"] == container_provider_id
            ]

        if container_provider_type:
            virtual_clusters = [
                virtual_cluster
                for virtual_cluster in virtual_clusters
                if virtual_cluster["containerProvider"]["type"]
                == container_provider_type
            ]

        if created_after:
            virtual_clusters = [
                virtual_cluster
                for virtual_cluster in virtual_clusters
                if virtual_cluster["createdAt"] >= created_after
            ]

        if created_before:
            virtual_clusters = [
                virtual_cluster
                for virtual_cluster in virtual_clusters
                if virtual_cluster["createdAt"] <= created_before
            ]

        if states:
            virtual_clusters = [
                virtual_cluster
                for virtual_cluster in virtual_clusters
                if virtual_cluster["state"] in states
            ]

        return paginated_list(virtual_clusters, max_results, next_token)

    def start_job_run(
        self,
        name,
        virtual_cluster_id,
        client_token,
        execution_role_arn,
        release_label,
        job_driver,
        configuration_overrides,
        tags,
    ):

        job = FakeJob(
            name=name,
            virtual_cluster_id=virtual_cluster_id,
            client_token=client_token,
            execution_role_arn=execution_role_arn,
            release_label=release_label,
            job_driver=job_driver,
            configuration_overrides=configuration_overrides,
            tags=tags,
            region_name=self.region_name,
            aws_partition=self.partition,
        )

        self.jobs[job.id] = job
        self.job_count += 1
        return job


emrcontainers_backends = {}
for available_region in Session().get_available_regions("emr-containers"):
    emrcontainers_backends[available_region] = EMRContainersBackend(available_region)
for available_region in Session().get_available_regions(
    "emr-containers", partition_name="aws-us-gov"
):
    emrcontainers_backends[available_region] = EMRContainersBackend(available_region)
for available_region in Session().get_available_regions(
    "emr-containers", partition_name="aws-cn"
):
    emrcontainers_backends[available_region] = EMRContainersBackend(available_region)
