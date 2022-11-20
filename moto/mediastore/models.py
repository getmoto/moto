from collections import OrderedDict
from datetime import date

from moto.core import BaseBackend, BackendDict, BaseModel
from .exceptions import (
    ContainerNotFoundException,
    ResourceNotFoundException,
    PolicyNotFoundException,
)


class Container(BaseModel):
    def __init__(self, **kwargs):
        self.arn = kwargs.get("arn")
        self.name = kwargs.get("name")
        self.endpoint = kwargs.get("endpoint")
        self.status = kwargs.get("status")
        self.creation_time = kwargs.get("creation_time")
        self.lifecycle_policy = None
        self.policy = None
        self.metric_policy = None
        self.tags = kwargs.get("tags")

    def to_dict(self, exclude=None):
        data = {
            "ARN": self.arn,
            "Name": self.name,
            "Endpoint": self.endpoint,
            "Status": self.status,
            "CreationTime": self.creation_time,
            "Tags": self.tags,
        }
        if exclude:
            for key in exclude:
                del data[key]
        return data


class MediaStoreBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._containers = OrderedDict()

    def create_container(self, name, tags):
        arn = f"arn:aws:mediastore:container:{name}"
        container = Container(
            arn=arn,
            name=name,
            endpoint=f"/{name}",
            status="CREATING",
            creation_time=date.today().strftime("%m/%d/%Y, %H:%M:%S"),
            tags=tags,
        )
        self._containers[name] = container
        return container

    def delete_container(self, name):
        if name not in self._containers:
            raise ContainerNotFoundException()
        del self._containers[name]
        return {}

    def describe_container(self, name):
        if name not in self._containers:
            raise ResourceNotFoundException()
        container = self._containers[name]
        container.status = "ACTIVE"
        return container

    def list_containers(self):
        """
        Pagination is not yet implemented
        """
        containers = list(self._containers.values())
        response_containers = [c.to_dict() for c in containers]
        return response_containers, None

    def list_tags_for_resource(self, name):
        if name not in self._containers:
            raise ContainerNotFoundException()
        tags = self._containers[name].tags
        return tags

    def put_lifecycle_policy(self, container_name, lifecycle_policy):
        if container_name not in self._containers:
            raise ResourceNotFoundException()
        self._containers[container_name].lifecycle_policy = lifecycle_policy
        return {}

    def get_lifecycle_policy(self, container_name):
        if container_name not in self._containers:
            raise ResourceNotFoundException()
        lifecycle_policy = self._containers[container_name].lifecycle_policy
        if not lifecycle_policy:
            raise PolicyNotFoundException()
        return lifecycle_policy

    def put_container_policy(self, container_name, policy):
        if container_name not in self._containers:
            raise ResourceNotFoundException()
        self._containers[container_name].policy = policy
        return {}

    def get_container_policy(self, container_name):
        if container_name not in self._containers:
            raise ResourceNotFoundException()
        policy = self._containers[container_name].policy
        if not policy:
            raise PolicyNotFoundException()
        return policy

    def put_metric_policy(self, container_name, metric_policy):
        if container_name not in self._containers:
            raise ResourceNotFoundException()
        self._containers[container_name].metric_policy = metric_policy
        return {}

    def get_metric_policy(self, container_name):
        if container_name not in self._containers:
            raise ResourceNotFoundException()
        metric_policy = self._containers[container_name].metric_policy
        if not metric_policy:
            raise PolicyNotFoundException()
        return metric_policy


mediastore_backends = BackendDict(MediaStoreBackend, "mediastore")
