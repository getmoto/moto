"""EMRContainersBackend class with methods for supported APIs."""
from datetime import datetime
from boto3 import Session

from moto.core import BaseBackend, BaseModel, ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds

from .utils import random_cluster_id, get_partition, paginated_list

# String Templates
from ..config.exceptions import ValidationException

VIRTUAL_CLUSTER_ARN_TEMPLATE = (
    "arn:{partition}:emr-containers:{region}:"
    + str(ACCOUNT_ID)
    + ":/virtualclusters/{virtual_cluster_id}"
)

# Defaults used for creating a Virtual cluster
ACTIVE_STATUS = "ACTIVE"


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
        self.state = ACTIVE_STATUS
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


class EMRContainersBackend(BaseBackend):
    """Implementation of EMRContainers APIs."""

    def __init__(self, region_name=None):
        super(EMRContainersBackend, self).__init__()
        self.virtual_clusters = dict()
        self.virtual_cluster_count = 0
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
