"""EMRContainersBackend class with methods for supported APIs."""
from datetime import datetime
from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_without_milliseconds




class FakeCluster(BaseModel):

    def __init__(self,
                 name,
                 container_provider,
                 client_token,
                 tags=None,
                 virtual_cluster_id= None):

        self.id = virtual_cluster_id

        self.name = name
        self.client_token = client_token
        self.arn = None
        self.state = None
        self.container_provider = container_provider
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.tags= tags


    def __iter__(self):
        yield "id", self.id
        yield "name", self.name
        yield "arn", self.arn
        yield "state", self.state
        yield "containerProvider", self.container_provider
        yield "createdAt", self.creation_date
        yield "tags", self.tags



class EMRContainersBackend(BaseBackend):
    """Implementation of EMRContainers APIs."""

    def __init__(self, region_name=None):
        self.virtual_clusters = dict()
        self.virtual_cluster_count = 0
        self.region_name = region_name

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_virtual_cluster(self,
                               name,
                               container_provider,
                               client_token,
                               tags = None):
        virtual_cluster = FakeCluster(
            name=name,
            container_provider=container_provider,
            client_token=client_token,
            tags= tags
        )

        self.virtual_clusters[name] = virtual_cluster
        self.virtual_cluster_count += 1
        return virtual_cluster


emrcontainers_backends = {}
for available_region in Session().get_available_regions("emr-containers"):
    emrcontainers_backends[available_region] = EMRContainersBackend(available_region)
for available_region in Session().get_available_regions("emr-containers", partition_name="aws-us-gov"):
    emrcontainers_backends[available_region] = EMRContainersBackend(available_region)
for available_region in Session().get_available_regions("emr-containers", partition_name="aws-cn"):
    emrcontainers_backends[available_region] = EMRContainersBackend(available_region)