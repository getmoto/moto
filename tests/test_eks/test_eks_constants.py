"""
This file should only contain constants used for the EKS tests.
"""
import re
from enum import Enum

from boto3 import Session

PARTITIONS = Session().get_available_partitions()
REGION = Session().region_name
SERVICE = "eks"
SUBNET_IDS = ["subnet-12345ab", "subnet-67890cd"]

AMI_TYPE_KEY = "amiType"
AMI_TYPE_VALUE = "AL2_x86_64"

CLIENT_REQUEST_TOKEN_KEY = "clientRequestToken"
CLIENT_REQUEST_TOKEN_VALUE = "test_request_token"

DISK_SIZE_KEY = "diskSize"
DISK_SIZE_VALUE = 30

ENCRYPTION_CONFIG_KEY = "encryptionConfig"
ENCRYPTION_CONFIG_VALUE = [
    {"resources": ["secrets"], "provider": {"keyArn": "arn:of:the:key"}}
]

INSTANCE_TYPES_KEY = "instanceTypes"
INSTANCE_TYPES_VALUE = ["t3.medium"]

KUBERNETES_NETWORK_CONFIG_KEY = "kubernetesNetworkConfig"
KUBERNETES_NETWORK_CONFIG_VALUE = {"serviceIpv4Cidr": "172.20.0.0/16"}

LABELS_KEY = "labels"
LABELS_VALUE = {"purpose": "example"}

LAUNCH_TEMPLATE_KEY = "launchTemplate"
LAUNCH_TEMPLATE_VALUE = {"name": "myTemplate", "version": "2", "id": "123456"}

LOGGING_KEY = "logging"
LOGGING_VALUE = {"clusterLogging": [{"types": ["api"], "enabled": True}]}

NODEROLE_ARN_KEY = "nodeRole"
NODEROLE_ARN_VALUE = "arn:aws:iam::123456789012:role/role_name"

REMOTE_ACCESS_KEY = "remoteAccess"
REMOTE_ACCESS_VALUE = {"ec2SshKey": "eksKeypair"}

RESOURCES_VPC_CONFIG_KEY = "resourcesVpcConfig"
RESOURCES_VPC_CONFIG_VALUE = {
    "subnetIds": SUBNET_IDS,
    "endpointPublicAccess": True,
    "endpointPrivateAccess": False,
}

ROLE_ARN_KEY = "roleArn"
ROLE_ARN_VALUE = "arn:aws:iam::123456789012:role/role_name"

SCALING_CONFIG_KEY = "scalingConfig"
SCALING_CONFIG_VALUE = {"minSize": 2, "maxSize": 3, "desiredSize": 2}

STATUS_KEY = "status"
STATUS_VALUE = "ACTIVE"

SUBNETS_KEY = "subnets"
SUBNETS_VALUE = SUBNET_IDS

TAGS_KEY = "tags"
TAGS_VALUE = {"hello": "world"}

TAINTS_KEY = "taints"
TAINTS_VALUE = [{"key": "manual_only", "value": "true", "effect": "NO_SCHEDULE"}]

VERSION_KEY = "version"
VERSION_VALUE = "1"

AMI_TYPE = (AMI_TYPE_KEY, AMI_TYPE_VALUE)
CLIENT_REQUEST_TOKEN = (CLIENT_REQUEST_TOKEN_KEY, CLIENT_REQUEST_TOKEN_VALUE)
DISK_SIZE = (DISK_SIZE_KEY, DISK_SIZE_VALUE)
ENCRYPTION_CONFIG = (ENCRYPTION_CONFIG_KEY, ENCRYPTION_CONFIG_VALUE)
INSTANCE_TYPES = (INSTANCE_TYPES_KEY, INSTANCE_TYPES_VALUE)
KUBERNETES_NETWORK_CONFIG = (
    KUBERNETES_NETWORK_CONFIG_KEY,
    KUBERNETES_NETWORK_CONFIG_VALUE,
)
LABELS = (LABELS_KEY, LABELS_VALUE)
LAUNCH_TEMPLATE = (LAUNCH_TEMPLATE_KEY, LAUNCH_TEMPLATE_VALUE)
LOGGING = (LOGGING_KEY, LOGGING_VALUE)
NODEROLE_ARN = (NODEROLE_ARN_KEY, NODEROLE_ARN_VALUE)
REMOTE_ACCESS = (REMOTE_ACCESS_KEY, REMOTE_ACCESS_VALUE)
RESOURCES_VPC_CONFIG = (RESOURCES_VPC_CONFIG_KEY, RESOURCES_VPC_CONFIG_VALUE)
ROLE_ARN = (ROLE_ARN_KEY, ROLE_ARN_VALUE)
SCALING_CONFIG = (SCALING_CONFIG_KEY, SCALING_CONFIG_VALUE)
STATUS = (STATUS_KEY, STATUS_VALUE)
SUBNETS = (SUBNETS_KEY, SUBNETS_VALUE)
TAGS = (TAGS_KEY, TAGS_VALUE)
TAINTS = (TAINTS_KEY, TAINTS_VALUE)
VERSION = (VERSION_KEY, VERSION_VALUE)


class ClusterInputs:
    REQUIRED = [ROLE_ARN, RESOURCES_VPC_CONFIG]
    OPTIONAL = [
        CLIENT_REQUEST_TOKEN,
        ENCRYPTION_CONFIG,
        LOGGING,
        KUBERNETES_NETWORK_CONFIG,
        TAGS,
        VERSION,
    ]


class NodegroupInputs:
    REQUIRED = [NODEROLE_ARN, SUBNETS]
    OPTIONAL = [
        AMI_TYPE,
        DISK_SIZE,
        INSTANCE_TYPES,
        LABELS,
        REMOTE_ACCESS,
        SCALING_CONFIG,
        TAGS,
    ]


class TestResults(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ResponseAttribute:
    CLUSTER = "cluster"
    CLUSTERS = "clusters"
    NEXT_TOKEN = "nextToken"
    NODEGROUP = "nodegroup"
    NODEGROUPS = "nodegroups"


class ClusterAttribute:
    ARN = "arn"
    CLIENT_REQUEST_TOKEN = "client_request_token"
    CLUSTER = "cluster"
    CLUSTER_NAME = "clusterName"
    CREATED_AT = "createdAt"
    ENDPOINT = "endpoint"
    IDENTITY = "identity"
    ISSUER = "issuer"
    NAME = "name"
    OIDC = "oidc"


class NodegroupAttribute:
    NAME = "nodegroupName"


class ArnAttributes:
    PARTITION = "partition"
    REGION = "region"
    ACCOUNT_ID = "account_id"
    CLUSTER_NAME = "cluster_name"


class BatchCountSize:
    SINGLE = 1
    SMALL = 10
    MEDIUM = 20
    LARGE = 200


class PageCount:
    SMALL = 3
    LARGE = 10


class ArnFormats:
    CLUSTER_ARN = re.compile(
        "arn:"
        + "(?P<partition>.+):"
        + "eks:"
        + "(?P<region>[-0-9a-zA-Z]+):"
        + "(?P<account_id>[0-9]{12}):"
        + "cluster/"
        + "(?P<cluster_name>.+)"
    )


class MethodNames:
    CREATE_NODEGROUP = "CreateNodegroup"
    DELETE_CLUSTER = "DeleteCluster"
    DESCRIBE_CLUSTER = "DescribeCluster"
