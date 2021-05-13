"""
This file should only contain constants used for the EKS tests.
"""
import re

from boto3 import Session

PARTITIONS = Session().get_available_partitions()
REGION = Session().region_name
SERVICE = "eks"

CLIENT_REQUEST_TOKEN_KEY = "clientRequestToken"
CLIENT_REQUEST_TOKEN_VALUE = "test_request_token"

ENCRYPTION_CONFIG_KEY = "encryptionConfig"
ENCRYPTION_CONFIG_VALUE = [
    {"resources": ["secrets"], "provider": {"keyArn": "arn:of:the:key"}}
]

KUBERNETES_NETWORK_CONFIG_KEY = "kubernetesNetworkConfig"
KUBERNETES_NETWORK_CONFIG_VALUE = {"serviceIpv4Cidr": "172.20.0.0/16"}

LOGGING_KEY = "logging"
LOGGING_VALUE = {"clusterLogging": [{"types": ["api"], "enabled": True}]}

RESOURCES_VPC_CONFIG_KEY = "resourcesVpcConfig"
RESOURCES_VPC_CONFIG_VALUE = {
    "subnetIds": ["subnet-12345ab", "subnet-67890cd"],
    "endpointPublicAccess": True,
    "endpointPrivateAccess": False,
}

ROLE_ARN_KEY = "roleArn"
ROLE_ARN_VALUE = "arn:aws:iam::123456789012:role/role_name"

STATUS_KEY = "status"
STATUS_VALUE = "ACTIVE"

TAGS_KEY = "tags"
TAGS_VALUE = {"hello": "world"}

VERSION_KEY = "version"
VERSION_VALUE = "1"

CLIENT_REQUEST_TOKEN = (CLIENT_REQUEST_TOKEN_KEY, CLIENT_REQUEST_TOKEN_VALUE)
ENCRYPTION_CONFIG = (ENCRYPTION_CONFIG_KEY, ENCRYPTION_CONFIG_VALUE)
KUBERNETES_NETWORK_CONFIG = (
    KUBERNETES_NETWORK_CONFIG_KEY,
    KUBERNETES_NETWORK_CONFIG_VALUE,
)
LOGGING = (LOGGING_KEY, LOGGING_VALUE)
RESOURCES_VPC_CONFIG = (RESOURCES_VPC_CONFIG_KEY, RESOURCES_VPC_CONFIG_VALUE)
ROLE_ARN = (ROLE_ARN_KEY, ROLE_ARN_VALUE)
STATUS = (STATUS_KEY, STATUS_VALUE)
TAGS = (TAGS_KEY, TAGS_VALUE)
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


class ResponseAttribute:
    CLUSTER = "cluster"
    CLUSTERS = "clusters"
    NEXT_TOKEN = "nextToken"


class ClusterAttribute:
    ARN = "arn"
    CLIENT_REQUEST_TOKEN = "client_request_token"
    CLUSTER = "cluster"
    CREATED_AT = "createdAt"
    ENDPOINT = "endpoint"
    IDENTITY = "identity"
    ISSUER = "issuer"
    NAME = "name"
    OIDC = "oidc"


class ArnAttributes:
    PARTITION = "partition"
    REGION = "region"
    ACCOUNT_ID = "account_id"
    CLUSTER_NAME = "cluster_name"


class BatchCountSize:
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


class MessageTemplates:
    ClusterNotFound = "Cluster {name} not found."
