from __future__ import unicode_literals

from boto3 import Session
from datetime import datetime
from moto.core import BaseBackend, ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from .exceptions import ResourceNotFoundException
from .utils import set_partition, validate_role_arn
from ..utilities.utils import random_string

ARN_TEMPLATE = "arn:{partition}:eks:{region}:" + str(ACCOUNT_ID) + ":cluster/{name}"
ISSUER_TEMPLATE = "https://oidc.eks.{region}.amazonaws.com/id/" + random_string(10)
ENDPOINT_TEMPLATE = (
    "https://"
    + random_string()
    + "."
    + random_string(3)
    + ".{region}.eks.amazonaws.com/"
)

DEFAULT_KUBERNETES_NETWORK_CONFIG = {"serviceIpv4Cidr": "172.20.0.0/16"}
DEFAULT_KUBERNETES_VERSION = "1.19"
DEFAULT_LOGGING = {
    "clusterLogging": [
        {
            "types": [
                "api",
                "audit",
                "authenticator",
                "controllerManager",
                "scheduler",
            ],
            "enabled": False,
        }
    ]
}
DEFAULT_PLATFORM_VERSION = "eks.4"
DEFAULT_STATUS = "ACTIVE"


class Cluster:
    def __init__(
        self,
        name,
        roleArn,
        resourcesVpcConfig,
        regionName,
        awsPartition,
        version=None,
        kubernetesNetworkConfig=None,
        logging=None,
        clientRequestToken=None,
        tags=None,
        encryptionConfig=None,
    ):
        self.nodegroups = dict()
        self.nodegroup_count = 0

        self.arn = ARN_TEMPLATE.format(
            partition=awsPartition, region=regionName, name=name
        )
        self.certificateAuthority = {"data": random_string(1400)}
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.identity = {"oidc": {"issuer": ISSUER_TEMPLATE.format(region=regionName)}}
        self.endpoint = ENDPOINT_TEMPLATE.format(region=regionName)

        self.kubernetes_network_config = (
            kubernetesNetworkConfig or DEFAULT_KUBERNETES_NETWORK_CONFIG
        )
        self.logging = logging or DEFAULT_LOGGING
        self.platformVersion = DEFAULT_PLATFORM_VERSION
        self.status = DEFAULT_STATUS
        self.version = version or DEFAULT_KUBERNETES_VERSION

        self.client_request_token = clientRequestToken
        self.encryption_config = encryptionConfig
        self.name = name
        self.resources_vpc_config = resourcesVpcConfig
        self.role_arn = roleArn
        self.tags = tags

    def __iter__(self):
        yield "name", self.name
        yield "arn", self.arn
        yield "createdAt", self.creation_date
        yield "version", self.version
        yield "endpoint", self.endpoint
        yield "roleArn", self.role_arn
        yield "resourcesVpcConfig", self.resources_vpc_config
        yield "kubernetesNetworkConfig", self.kubernetes_network_config
        yield "logging", self.logging
        yield "identity", self.identity
        yield "status", self.status
        yield "certificateAuthority", self.certificateAuthority
        yield "clientRequestToken", self.client_request_token
        yield "platformVersion", self.platformVersion
        yield "tags", self.tags
        yield "encryptionConfig", self.encryption_config


class EKSBackend(BaseBackend):
    def __init__(self, region_name):
        super(EKSBackend, self).__init__()
        self.clusters = dict()
        self.cluster_count = 0
        self.region_name = region_name
        self.partition = set_partition(region_name)

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def list_clusters(self, max_results, next_token):
        cluster_names = sorted(self.clusters.keys())
        start = cluster_names.index(next_token) if next_token else 0
        end = min(start + max_results, self.cluster_count)
        new_next = "null" if end == self.cluster_count else cluster_names[end]

        return cluster_names[start:end], new_next

    def create_cluster(
        self,
        name,
        role_arn,
        resources_vpc_config,
        version=None,
        kubernetes_network_config=None,
        logging=None,
        client_request_token=None,
        tags=None,
        encryption_config=None,
    ):
        if tags is None:
            tags = dict()
        validate_role_arn(role_arn)

        cluster = Cluster(
            name=name,
            roleArn=role_arn,
            resourcesVpcConfig=resources_vpc_config,
            version=version,
            kubernetesNetworkConfig=kubernetes_network_config,
            logging=logging,
            clientRequestToken=client_request_token,
            tags=tags,
            encryptionConfig=encryption_config,
            regionName=self.region_name,
            awsPartition=self.partition,
        )
        self.clusters[name] = cluster
        self.cluster_count += 1
        return cluster

    def describe_cluster(self, name):
        try:
            return self.clusters[name]
        except KeyError:
            raise ResourceNotFoundException("Cluster " + name + " not found.")

    def delete_cluster(self, name):
        # TODO: Nodegroups not implemented yet; ensure that this
        #       is updated so that it acts appropriately when
        #       deleting a cluster which contains nodegroups
        if name not in self.clusters:
            raise ResourceNotFoundException("Cluster " + name + " not found.")
        else:
            result = self.clusters.pop(name)
            self.cluster_count -= 1
            return result

    def list_nodegroups(self, cluster_name, max_results, next_token):
        cluster = self.clusters[cluster_name]
        nodegroup_names = sorted(cluster.nodegroups.keys())
        start = nodegroup_names.index(next_token) if next_token else 0
        end = min(start + max_results, cluster.nodegroup_count)
        new_next = "null" if end == cluster.nodegroup_count else nodegroup_names[end]

        return nodegroup_names[start:end], new_next


eks_backends = {}
for region in Session().get_available_regions("eks"):
    eks_backends[region] = EKSBackend(region)
for region in Session().get_available_regions("eks", partition_name="aws-us-gov"):
    eks_backends[region] = EKSBackend(region)
for region in Session().get_available_regions("eks", partition_name="aws-cn"):
    eks_backends[region] = EKSBackend(region)
