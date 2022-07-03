from datetime import datetime
from uuid import uuid4

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_without_milliseconds, BackendDict

from ..utilities.utils import random_string
from .exceptions import (
    InvalidParameterException,
    InvalidRequestException,
    ResourceInUseException,
    ResourceNotFoundException,
)
from .utils import get_partition, validate_role_arn

# String Templates
CLUSTER_ARN_TEMPLATE = "arn:{partition}:eks:{region}:{account_id}:cluster/{name}"
FARGATE_PROFILE_ARN_TEMPLATE = "arn:{partition}:eks:{region}:{account_id}:fargateprofile/{cluster_name}/{fargate_profile_name}/{uuid}"
NODEGROUP_ARN_TEMPLATE = "arn:{partition}:eks:{region}:{account_id}:nodegroup/{cluster_name}/{nodegroup_name}/{uuid}"
ISSUER_TEMPLATE = "https://oidc.eks.{region}.amazonaws.com/id/" + random_string(10)
ENDPOINT_TEMPLATE = (
    "https://"
    + random_string()
    + "."
    + random_string(3)
    + ".{region}.eks.amazonaws.com/"
)

# Defaults used for creating a Cluster
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
ACTIVE_STATUS = "ACTIVE"

# Defaults used for creating a Managed Nodegroup
DEFAULT_AMI_TYPE = "AL2_x86_64"
DEFAULT_CAPACITY_TYPE = "ON_DEMAND"
DEFAULT_DISK_SIZE = "20"
DEFAULT_INSTANCE_TYPES = ["t3.medium"]
DEFAULT_NODEGROUP_HEALTH = {"issues": []}
DEFAULT_RELEASE_VERSION = "1.19.8-20210414"
DEFAULT_REMOTE_ACCESS = {"ec2SshKey": "eksKeypair"}
DEFAULT_SCALING_CONFIG = {"minSize": 2, "maxSize": 2, "desiredSize": 2}

# Exception messages, also imported into testing.
# Obtained through cURL responses from the actual APIs.
CLUSTER_IN_USE_MSG = "Cluster has nodegroups attached"
CLUSTER_EXISTS_MSG = "Cluster already exists with name: {clusterName}"
CLUSTER_NOT_FOUND_MSG = "No cluster found for name: {clusterName}."
CLUSTER_NOT_READY_MSG = "Cluster '{clusterName}' is not in ACTIVE status"
FARGATE_PROFILE_EXISTS_MSG = (
    "A Fargate Profile already exists with this name in this cluster."
)
FARGATE_PROFILE_NEEDS_SELECTOR_MSG = "Fargate Profile requires at least one selector."
FARGATE_PROFILE_NOT_FOUND_MSG = (
    "No Fargate Profile found with name: {fargateProfileName}."
)
FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE = (
    "Fargate Profile must have at least one selector with at least one namespace value."
)
FARGATE_PROFILE_TOO_MANY_LABELS = (
    "Request contains Selector with more than 5 Label pairs"
)
LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG = (
    "Disk size must be specified within the launch template."
)
LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG = (
    "Remote access configuration cannot be specified with a launch template."
)
NODEGROUP_EXISTS_MSG = (
    "NodeGroup already exists with name {nodegroupName} and cluster name {clusterName}"
)
NODEGROUP_NOT_FOUND_MSG = "No node group found for name: {nodegroupName}."


class Cluster:
    def __init__(
        self,
        name,
        role_arn,
        resources_vpc_config,
        account_id,
        region_name,
        aws_partition,
        version=None,
        kubernetes_network_config=None,
        logging=None,
        client_request_token=None,
        tags=None,
        encryption_config=None,
    ):
        if encryption_config is None:
            encryption_config = []
        if tags is None:
            tags = dict()

        self.nodegroups = dict()
        self.nodegroup_count = 0

        self.fargate_profiles = dict()
        self.fargate_profile_count = 0

        self.arn = CLUSTER_ARN_TEMPLATE.format(
            partition=aws_partition,
            account_id=account_id,
            region=region_name,
            name=name,
        )
        self.certificateAuthority = {"data": random_string(1400)}
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.identity = {"oidc": {"issuer": ISSUER_TEMPLATE.format(region=region_name)}}
        self.endpoint = ENDPOINT_TEMPLATE.format(region=region_name)

        self.kubernetes_network_config = (
            kubernetes_network_config or DEFAULT_KUBERNETES_NETWORK_CONFIG
        )
        self.logging = logging or DEFAULT_LOGGING
        self.platformVersion = DEFAULT_PLATFORM_VERSION
        self.status = ACTIVE_STATUS
        self.version = version or DEFAULT_KUBERNETES_VERSION

        self.client_request_token = client_request_token
        self.encryption_config = encryption_config
        self.name = name
        self.resources_vpc_config = resources_vpc_config
        self.role_arn = role_arn
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

    def isActive(self):
        return self.status == "ACTIVE"


class FargateProfile:
    def __init__(
        self,
        cluster_name,
        fargate_profile_name,
        pod_execution_role_arn,
        selectors,
        account_id,
        region_name,
        aws_partition,
        client_request_token=None,
        subnets=None,
        tags=None,
    ):
        if subnets is None:
            subnets = list()
        if tags is None:
            tags = dict()

        self.created_at = iso_8601_datetime_without_milliseconds(datetime.now())
        self.uuid = str(uuid4())
        self.fargate_profile_arn = FARGATE_PROFILE_ARN_TEMPLATE.format(
            partition=aws_partition,
            account_id=account_id,
            region=region_name,
            cluster_name=cluster_name,
            fargate_profile_name=fargate_profile_name,
            uuid=self.uuid,
        )

        self.status = ACTIVE_STATUS
        self.cluster_name = cluster_name
        self.fargate_profile_name = fargate_profile_name
        self.pod_execution_role_arn = pod_execution_role_arn
        self.client_request_token = client_request_token
        self.selectors = selectors
        self.subnets = subnets
        self.tags = tags

    def __iter__(self):
        yield "clusterName", self.cluster_name
        yield "createdAt", self.created_at
        yield "fargateProfileArn", self.fargate_profile_arn
        yield "fargateProfileName", self.fargate_profile_name
        yield "podExecutionRoleArn", self.pod_execution_role_arn
        yield "selectors", self.selectors
        yield "subnets", self.subnets
        yield "status", self.status
        yield "tags", self.tags


class ManagedNodegroup:
    def __init__(
        self,
        cluster_name,
        node_role,
        nodegroup_name,
        subnets,
        account_id,
        region_name,
        aws_partition,
        scaling_config=None,
        disk_size=None,
        instance_types=None,
        ami_type=None,
        remote_access=None,
        labels=None,
        taints=None,
        tags=None,
        client_request_token=None,
        launch_template=None,
        capacity_type=None,
        version=None,
        release_version=None,
    ):
        if tags is None:
            tags = dict()
        if labels is None:
            labels = dict()
        if taints is None:
            taints = dict()

        self.uuid = str(uuid4())
        self.arn = NODEGROUP_ARN_TEMPLATE.format(
            partition=aws_partition,
            account_id=account_id,
            region=region_name,
            cluster_name=cluster_name,
            nodegroup_name=nodegroup_name,
            uuid=self.uuid,
        )
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.modified_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.health = DEFAULT_NODEGROUP_HEALTH
        self.resources = {
            "autoScalingGroups": [{"name": "eks-" + self.uuid}],
            "remoteAccessSecurityGroup": "sg-" + random_string(17).lower(),
        }

        self.ami_type = ami_type or DEFAULT_AMI_TYPE
        self.capacity_type = capacity_type or DEFAULT_CAPACITY_TYPE
        self.disk_size = disk_size or DEFAULT_DISK_SIZE
        self.instance_types = instance_types or DEFAULT_INSTANCE_TYPES
        self.release_version = release_version or DEFAULT_RELEASE_VERSION
        self.remote_access = remote_access or DEFAULT_REMOTE_ACCESS
        self.scaling_config = scaling_config or DEFAULT_SCALING_CONFIG
        self.status = ACTIVE_STATUS
        self.version = version or DEFAULT_KUBERNETES_VERSION

        self.client_request_token = client_request_token
        self.cluster_name = cluster_name
        self.labels = labels
        self.launch_template = launch_template
        self.node_role = node_role
        self.nodegroup_name = nodegroup_name
        self.partition = aws_partition
        self.region = region_name
        self.subnets = subnets
        self.tags = tags
        self.taints = taints

    def __iter__(self):
        yield "nodegroupName", self.nodegroup_name
        yield "nodegroupArn", self.arn
        yield "clusterName", self.cluster_name
        yield "version", self.version
        yield "releaseVersion", self.release_version
        yield "createdAt", self.creation_date
        yield "modifiedAt", self.modified_date
        yield "status", self.status
        yield "capacityType", self.capacity_type
        yield "scalingConfig", self.scaling_config
        yield "instanceTypes", self.instance_types
        yield "subnets", self.subnets
        yield "remoteAccess", self.remote_access
        yield "amiType", self.ami_type
        yield "nodeRole", self.node_role
        yield "labels", self.labels
        yield "taints", self.taints
        yield "resources", self.resources
        yield "diskSize", self.disk_size
        yield "health", self.health
        yield "launchTemplate", self.launch_template
        yield "tags", self.tags


class EKSBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.clusters = dict()
        self.cluster_count = 0
        self.partition = get_partition(region_name)

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
        if name in self.clusters:
            # Cluster exists.
            raise ResourceInUseException(
                clusterName=name,
                nodegroupName=None,
                addonName=None,
                message=CLUSTER_EXISTS_MSG.format(clusterName=name),
            )
        validate_role_arn(role_arn)

        cluster = Cluster(
            name=name,
            role_arn=role_arn,
            resources_vpc_config=resources_vpc_config,
            version=version,
            kubernetes_network_config=kubernetes_network_config,
            logging=logging,
            client_request_token=client_request_token,
            tags=tags,
            encryption_config=encryption_config,
            account_id=self.account_id,
            region_name=self.region_name,
            aws_partition=self.partition,
        )
        self.clusters[name] = cluster
        self.cluster_count += 1
        return cluster

    def create_fargate_profile(
        self,
        fargate_profile_name,
        cluster_name,
        selectors,
        pod_execution_role_arn,
        subnets=None,
        client_request_token=None,
        tags=None,
    ):
        try:
            # Cluster exists.
            cluster = self.clusters[cluster_name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=cluster_name),
            )
        if fargate_profile_name in cluster.fargate_profiles:
            # Fargate Profile already exists.
            raise ResourceInUseException(
                clusterName=None,
                nodegroupName=None,
                addonName=None,
                message=FARGATE_PROFILE_EXISTS_MSG,
            )
        if not cluster.isActive():
            raise InvalidRequestException(
                message=CLUSTER_NOT_READY_MSG.format(clusterName=cluster_name)
            )

        _validate_fargate_profile_selectors(selectors)

        fargate_profile = FargateProfile(
            cluster_name=cluster_name,
            fargate_profile_name=fargate_profile_name,
            pod_execution_role_arn=pod_execution_role_arn,
            client_request_token=client_request_token,
            selectors=selectors,
            subnets=subnets,
            tags=tags,
            account_id=self.account_id,
            region_name=self.region_name,
            aws_partition=self.partition,
        )

        cluster.fargate_profiles[fargate_profile_name] = fargate_profile
        cluster.fargate_profile_count += 1
        return fargate_profile

    def create_nodegroup(
        self,
        cluster_name,
        node_role,
        nodegroup_name,
        subnets,
        scaling_config=None,
        disk_size=None,
        instance_types=None,
        ami_type=None,
        remote_access=None,
        labels=None,
        taints=None,
        tags=None,
        client_request_token=None,
        launch_template=None,
        capacity_type=None,
        version=None,
        release_version=None,
    ):
        try:
            # Cluster exists.
            cluster = self.clusters[cluster_name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=cluster_name),
            )
        if nodegroup_name in cluster.nodegroups:
            # Nodegroup already exists.
            raise ResourceInUseException(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name,
                addonName=None,
                message=NODEGROUP_EXISTS_MSG.format(
                    nodegroupName=nodegroup_name, clusterName=cluster_name
                ),
            )
        if not cluster.isActive():
            raise InvalidRequestException(
                message=CLUSTER_NOT_READY_MSG.format(clusterName=cluster_name)
            )
        if launch_template:
            validate_launch_template_combination(disk_size, remote_access)
        validate_role_arn(node_role)

        nodegroup = ManagedNodegroup(
            cluster_name=cluster_name,
            node_role=node_role,
            nodegroup_name=nodegroup_name,
            subnets=subnets,
            scaling_config=scaling_config,
            disk_size=disk_size,
            instance_types=instance_types,
            ami_type=ami_type,
            remote_access=remote_access,
            labels=labels,
            taints=taints,
            tags=tags,
            client_request_token=client_request_token,
            launch_template=launch_template,
            capacity_type=capacity_type,
            version=version,
            release_version=release_version,
            account_id=self.account_id,
            region_name=self.region_name,
            aws_partition=self.partition,
        )

        cluster.nodegroups[nodegroup_name] = nodegroup
        cluster.nodegroup_count += 1
        return nodegroup

    def describe_cluster(self, name):
        try:
            # Cluster exists.
            return self.clusters[name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=name),
            )

    def describe_fargate_profile(self, cluster_name, fargate_profile_name):
        try:
            # Cluster exists.
            cluster = self.clusters[cluster_name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=cluster_name,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=cluster_name),
            )
        try:
            # Fargate Profile exists.
            return cluster.fargate_profiles[fargate_profile_name]
        except KeyError:
            # Fargate Profile does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=FARGATE_PROFILE_NOT_FOUND_MSG.format(
                    fargateProfileName=fargate_profile_name
                ),
            )

    def describe_nodegroup(self, cluster_name, nodegroup_name):
        try:
            # Cluster exists.
            cluster = self.clusters[cluster_name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=cluster_name),
            )
        try:
            # Nodegroup exists.
            return cluster.nodegroups[nodegroup_name]
        except KeyError:
            # Nodegroup does not exist.
            raise ResourceNotFoundException(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name,
                fargateProfileName=None,
                addonName=None,
                message=NODEGROUP_NOT_FOUND_MSG.format(nodegroupName=nodegroup_name),
            )

    def delete_cluster(self, name):
        try:
            # Cluster exists.
            validate_safe_to_delete(self.clusters[name])
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=name),
            )

        result = self.clusters.pop(name)
        self.cluster_count -= 1
        return result

    def delete_fargate_profile(self, cluster_name, fargate_profile_name):
        try:
            # Cluster exists.
            cluster = self.clusters[cluster_name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=cluster_name,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=cluster_name),
            )
        try:
            # Fargate Profile exists.
            deleted_fargate_profile = cluster.fargate_profiles.pop(fargate_profile_name)
        except KeyError:
            # Fargate Profile does not exist.
            raise ResourceNotFoundException(
                clusterName=cluster_name,
                nodegroupName=None,
                fargateProfileName=fargate_profile_name,
                addonName=None,
                message=FARGATE_PROFILE_NOT_FOUND_MSG.format(
                    fargateProfileName=fargate_profile_name
                ),
            )

        cluster.fargate_profile_count -= 1
        return deleted_fargate_profile

    def delete_nodegroup(self, cluster_name, nodegroup_name):
        try:
            # Cluster exists.
            cluster = self.clusters[cluster_name]
        except KeyError:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message=CLUSTER_NOT_FOUND_MSG.format(clusterName=cluster_name),
            )
        try:
            # Nodegroup exists.
            result = cluster.nodegroups.pop(nodegroup_name)
        except KeyError:
            # Nodegroup does not exist.
            raise ResourceNotFoundException(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name,
                fargateProfileName=None,
                addonName=None,
                message=NODEGROUP_NOT_FOUND_MSG.format(nodegroupName=nodegroup_name),
            )

        cluster.nodegroup_count -= 1
        return result

    def tag_resource(self, resource_arn, tags):
        """
        This function currently will tag an EKS cluster only.  It does not tag a managed node group
        """

        try:
            cluster = next(
                self.clusters[x]
                for x in self.clusters
                if self.clusters[x].arn == resource_arn
            )
        except StopIteration:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message="An error occurred (NotFoundException) when calling the TagResource operation: Resource was not found",
            )
        cluster.tags.update(tags)
        return ""

    def untag_resource(self, resource_arn, tag_keys):
        """
        This function currently will remove tags on an EKS cluster only.  It does not remove tags from a managed node group
        """
        if not isinstance(tag_keys, list):
            tag_keys = [tag_keys]

        try:
            cluster = next(
                self.clusters[x]
                for x in self.clusters
                if self.clusters[x].arn == resource_arn
            )
        except StopIteration:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message="An error occurred (NotFoundException) when calling the UntagResource operation: Resource was not found",
            )
        for name in tag_keys:
            if name in cluster.tags:
                del cluster.tags[name]
        return ""

    def list_tags_for_resource(self, resource_arn):
        """
        This function currently will list tags on an EKS cluster only.  It does not list tags from a managed node group
        """

        try:
            cluster = next(
                self.clusters[x]
                for x in self.clusters
                if self.clusters[x].arn == resource_arn
            )
        except StopIteration:
            # Cluster does not exist.
            raise ResourceNotFoundException(
                clusterName=None,
                nodegroupName=None,
                fargateProfileName=None,
                addonName=None,
                message="An error occurred (NotFoundException) when calling the ListTagsForResource operation: Resource was not found",
            )
        return cluster.tags

    def list_clusters(self, max_results, next_token):
        return paginated_list(self.clusters.keys(), max_results, next_token)

    def list_fargate_profiles(self, cluster_name, max_results, next_token):
        cluster = self.clusters[cluster_name]
        return paginated_list(cluster.fargate_profiles.keys(), max_results, next_token)

    def list_nodegroups(self, cluster_name, max_results, next_token):
        cluster = self.clusters[cluster_name]
        return paginated_list(cluster.nodegroups.keys(), max_results, next_token)


def paginated_list(full_list, max_results, next_token):
    """
    Returns a tuple containing a slice of the full list
    starting at next_token and ending with at most the
    max_results number of elements, and the new
    next_token which can be passed back in for the next
    segment of the full list.
    """
    sorted_list = sorted(full_list)
    list_len = len(sorted_list)

    start = sorted_list.index(next_token) if next_token else 0
    end = min(start + max_results, list_len)
    new_next = None if end == list_len else sorted_list[end]

    return sorted_list[start:end], new_next


def validate_safe_to_delete(cluster):
    # A cluster which has nodegroups attached can not be deleted.
    if cluster.nodegroup_count:
        nodegroup_names = ",".join(list(cluster.nodegroups.keys()))
        raise ResourceInUseException(
            clusterName=cluster.name,
            nodegroupName=nodegroup_names,
            addonName=None,
            message=CLUSTER_IN_USE_MSG,
        )


def validate_launch_template_combination(disk_size, remote_access):
    if not (disk_size or remote_access):
        return

    raise InvalidParameterException(
        message=LAUNCH_TEMPLATE_WITH_DISK_SIZE_MSG
        if disk_size
        else LAUNCH_TEMPLATE_WITH_REMOTE_ACCESS_MSG
    )


def _validate_fargate_profile_selectors(selectors):
    def raise_exception(message):
        raise InvalidParameterException(
            clusterName=None,
            nodegroupName=None,
            fargateProfileName=None,
            addonName=None,
            message=message,
        )

    # At least one Selector must exist
    if not selectors:
        raise_exception(message=FARGATE_PROFILE_NEEDS_SELECTOR_MSG)

    for selector in selectors:
        # Every existing Selector must have a namespace
        if "namespace" not in selector:
            raise_exception(message=FARGATE_PROFILE_SELECTOR_NEEDS_NAMESPACE)
        # If a selector has labels, it can not have more than 5
        if len(selector.get("labels", {})) > 5:
            raise_exception(message=FARGATE_PROFILE_TOO_MANY_LABELS)


eks_backends = BackendDict(EKSBackend, "eks")
