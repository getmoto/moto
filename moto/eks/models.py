from __future__ import unicode_literals

import re

from boto3 import Session
from datetime import datetime
from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.sts.models import ACCOUNT_ID
from .exceptions import InvalidParameterException
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
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.status = "ACTIVE"
        self.platformVersion = "1.9"
        self.arn = ARN_TEMPLATE.format(
            partition=awsPartition, region=regionName, name=name
        )
        self.endpoint = ENDPOINT_TEMPLATE.format(region=regionName)
        self.identity = {"oidc": {"issuer": ISSUER_TEMPLATE.format(region=regionName)}}
        self.certificateAuthority = {"data": random_string(1400)}

        self.name = name
        self.role_arn = roleArn
        self.resources_vpc_config = resourcesVpcConfig
        self.version = version
        self.kubernetes_network_config = kubernetesNetworkConfig
        self.logging = logging
        self.client_request_token = clientRequestToken
        self.tags = tags
        self.encryption_config = encryptionConfig

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
        self.partition = self._set_partition()

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
        self._validate_role_arn(role_arn)

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

    def _set_partition(self):
        if region.startswith("cn-"):
            return "aws-cn"
        elif region.startswith("us-gov-"):
            return "aws-us-gov"
        elif region.startswith("us-gov-iso-"):
            return "aws-iso"
        elif region.startswith("us-gov-iso-b-"):
            return "aws-iso-b"
        else:
            return "aws"

    def _validate_role_arn(self, arn):
        valid_role_arn_format = re.compile(
            "arn:(?P<partition>.+):iam::(?P<account_id>[0-9]{12}):role/.+"
        )
        match = valid_role_arn_format.match(arn)
        valid_partition = (
            match.group("partition") in Session().get_available_partitions()
        )

        if not all({arn, match, valid_partition}):
            raise InvalidParameterException("Invalid Role Arn: '" + arn + "'")


eks_backends = {}
for region in Session().get_available_regions("eks"):
    eks_backends[region] = EKSBackend(region)
for region in Session().get_available_regions("eks", partition_name="aws-us-gov"):
    eks_backends[region] = EKSBackend(region)
for region in Session().get_available_regions("eks", partition_name="aws-cn"):
    eks_backends[region] = EKSBackend(region)
