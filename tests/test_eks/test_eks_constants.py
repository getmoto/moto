"""
This file should only contain constants used for the EKS tests.
"""
import re
from enum import Enum

from boto3 import Session

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.eks import REGION as DEFAULT_REGION

DEFAULT_ENCODING = "utf-8"
DEFAULT_HTTP_HEADERS = {"Content-type": "application/json"}
DEFAULT_NAMESPACE = "namespace_1"
FROZEN_TIME = "2013-11-27T01:42:00Z"
MAX_FARGATE_LABELS = 5
PARTITIONS = Session().get_available_partitions()
REGION = Session().region_name or DEFAULT_REGION
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
NODEROLE_ARN_VALUE = "arn:aws:iam::" + str(ACCOUNT_ID) + ":role/role_name"

POD_EXECUTION_ROLE_ARN_KEY = "podExecutionRoleArn"
POD_EXECUTION_ROLE_ARN_VALUE = "arn:aws:iam::" + str(ACCOUNT_ID) + ":role/role_name"

REMOTE_ACCESS_KEY = "remoteAccess"
REMOTE_ACCESS_VALUE = {"ec2SshKey": "eksKeypair"}

RESOURCES_VPC_CONFIG_KEY = "resourcesVpcConfig"
RESOURCES_VPC_CONFIG_VALUE = {
    "subnetIds": SUBNET_IDS,
    "endpointPublicAccess": True,
    "endpointPrivateAccess": False,
}

ROLE_ARN_KEY = "roleArn"
ROLE_ARN_VALUE = "arn:aws:iam::" + str(ACCOUNT_ID) + ":role/role_name"

SCALING_CONFIG_KEY = "scalingConfig"
SCALING_CONFIG_VALUE = {"minSize": 2, "maxSize": 3, "desiredSize": 2}

SELECTORS_KEY = "selectors"
SELECTORS_VALUE = [{"namespace": "profile-namespace"}]

STATUS_KEY = "status"
STATUS_VALUE = "ACTIVE"

SUBNETS_KEY = "subnets"
SUBNETS_VALUE = SUBNET_IDS

TAGS_KEY = "tags"
TAGS_VALUE = {"hello": "world"}

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
POD_EXECUTION_ROLE_ARN = (POD_EXECUTION_ROLE_ARN_KEY, POD_EXECUTION_ROLE_ARN_VALUE)
REMOTE_ACCESS = (REMOTE_ACCESS_KEY, REMOTE_ACCESS_VALUE)
RESOURCES_VPC_CONFIG = (RESOURCES_VPC_CONFIG_KEY, RESOURCES_VPC_CONFIG_VALUE)
ROLE_ARN = (ROLE_ARN_KEY, ROLE_ARN_VALUE)
SCALING_CONFIG = (SCALING_CONFIG_KEY, SCALING_CONFIG_VALUE)
SELECTORS = (SELECTORS_KEY, SELECTORS_VALUE)
STATUS = (STATUS_KEY, STATUS_VALUE)
SUBNETS = (SUBNETS_KEY, SUBNETS_VALUE)
TAGS = (TAGS_KEY, TAGS_VALUE)
VERSION = (VERSION_KEY, VERSION_VALUE)


class ResponseAttributes:
    CLUSTER = "cluster"
    CLUSTERS = "clusters"
    FARGATE_PROFILE_NAMES = "fargateProfileNames"
    FARGATE_PROFILE = "fargateProfile"
    MESSAGE = "message"
    NEXT_TOKEN = "nextToken"
    NODEGROUP = "nodegroup"
    NODEGROUPS = "nodegroups"


class ErrorAttributes:
    CODE = "Code"
    ERROR = "Error"
    MESSAGE = "Message"


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


class FargateProfileInputs:
    REQUIRED = [POD_EXECUTION_ROLE_ARN, SELECTORS]
    OPTIONAL = [SUBNETS, TAGS]


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


class PossibleTestResults(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AddonAttributes:
    ADDON_NAME = "addonName"


class ClusterAttributes:
    ARN = "arn"
    CLUSTER_NAME = "clusterName"
    CREATED_AT = "createdAt"
    ENDPOINT = "endpoint"
    IDENTITY = "identity"
    ISSUER = "issuer"
    NAME = "name"
    OIDC = "oidc"
    ENCRYPTION_CONFIG = "encryptionConfig"


class FargateProfileAttributes:
    ARN = "fargateProfileArn"
    CREATED_AT = "createdAt"
    FARGATE_PROFILE_NAME = "fargateProfileName"
    LABELS = "labels"
    NAMESPACE = "namespace"
    SELECTORS = "selectors"


class NodegroupAttributes:
    ARN = "nodegroupArn"
    AUTOSCALING_GROUPS = "autoScalingGroups"
    CREATED_AT = "createdAt"
    MODIFIED_AT = "modifiedAt"
    NAME = "name"
    NODEGROUP_NAME = "nodegroupName"
    REMOTE_ACCESS_SG = "remoteAccessSecurityGroup"
    RESOURCES = "resources"


class BatchCountSize:
    SINGLE = 1
    SMALL = 10
    MEDIUM = 20
    LARGE = 200


class PageCount:
    SMALL = 3
    LARGE = 10


FARGATE_PROFILE_UUID_PATTERN = "(?P<fargate_uuid>[-0-9a-z]{8}-[-0-9a-z]{4}-[-0-9a-z]{4}-[-0-9a-z]{4}-[-0-9a-z]{12})"
NODEGROUP_UUID_PATTERN = "(?P<nodegroup_uuid>[-0-9a-z]{8}-[-0-9a-z]{4}-[-0-9a-z]{4}-[-0-9a-z]{4}-[-0-9a-z]{12})"


class RegExTemplates:
    CLUSTER_ARN = re.compile(
        "arn:"
        + "(?P<partition>.+):"
        + "eks:"
        + "(?P<region>[-0-9a-zA-Z]+):"
        + "(?P<account_id>[0-9]{12}):"
        + "cluster/"
        + "(?P<cluster_name>.+)"
    )
    FARGATE_PROFILE_ARN = re.compile(
        "arn:"
        + "(?P<partition>.+):"
        + "eks:"
        + "(?P<region>[-0-9a-zA-Z]+):"
        + "(?P<account_id>[0-9]{12}):"
        + "fargateprofile/"
        + "(?P<cluster_name>.+)/"
        + "(?P<fargate_name>.+)/"
        + FARGATE_PROFILE_UUID_PATTERN
    )
    ISO8601_FORMAT = re.compile(
        r"^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$"
    )
    NODEGROUP_ARN = re.compile(
        "arn:"
        + "(?P<partition>.+):"
        + "eks:"
        + "(?P<region>[-0-9a-zA-Z]+):"
        + "(?P<account_id>[0-9]{12}):"
        + "nodegroup/"
        + "(?P<cluster_name>.+)/"
        + "(?P<nodegroup_name>.+)/"
        + NODEGROUP_UUID_PATTERN
    )
    NODEGROUP_ASG_NAME_PATTERN = re.compile("eks-" + NODEGROUP_UUID_PATTERN)
    NODEGROUP_SECURITY_GROUP_NAME_PATTERN = re.compile("sg-" + "([-0-9a-z]{17})")


class Endpoints:
    CREATE_CLUSTER = "/clusters"
    CREATE_NODEGROUP = "/clusters/{clusterName}/node-groups"
    DESCRIBE_CLUSTER = "/clusters/{clusterName}"
    DESCRIBE_NODEGROUP = "/clusters/{clusterName}/node-groups/{nodegroupName}"
    DELETE_CLUSTER = "/clusters/{clusterName}"
    DELETE_NODEGROUP = "/clusters/{clusterName}/node-groups/{nodegroupName}"
    LIST_CLUSTERS = "/clusters?maxResults={maxResults}&nextToken={nextToken}"
    LIST_NODEGROUPS = "/clusters/{clusterName}/node-groups?maxResults={maxResults}&nextToken={nextToken}"


class StatusCodes:
    OK = 200


class HttpHeaders:
    ErrorType = "x-amzn-ErrorType"
