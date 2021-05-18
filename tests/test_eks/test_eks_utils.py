from copy import deepcopy
from urllib.parse import urlparse

from moto.utilities.utils import random_string
from tests.test_eks.test_eks_constants import (
    ClusterInputs,
    ClusterAttribute,
    NodegroupInputs,
    ResponseAttribute,
    NodegroupAttribute,
)


def generate_clusters(client, num_clusters, minimal):
    return _pruned(
        [
            client.create_cluster(
                name=random_string(), **_input_builder(ClusterInputs, minimal)
            )[ResponseAttribute.CLUSTER][ClusterAttribute.NAME]
            for _ in range(num_clusters)
        ]
    )


def generate_nodegroups(client, cluster_name, num_nodegroups, minimal):
    return _pruned(
        [
            client.create_nodegroup(
                nodegroupName=random_string(),
                clusterName=cluster_name,
                **_input_builder(NodegroupInputs, minimal)
            )[ResponseAttribute.NODEGROUP][NodegroupAttribute.NAME]
            for _ in range(num_nodegroups)
        ]
    )


def is_valid_uri(value):
    result = urlparse(value)
    return all([result.scheme, result.netloc, result.path])


def region_matches_partition(region, partition):
    valid_matches = [
        ("cn-", "aws-cn"),
        ("us-gov-", "aws-us-gov"),
        ("us-gov-iso-", "aws-iso"),
        ("us-gov-iso-b-", "aws-iso-b"),
    ]

    for prefix, expected_partition in valid_matches:
        if region.startswith(prefix):
            return partition == expected_partition
    return partition == "aws"


def _input_builder(options, minimal):
    values = deepcopy(options.REQUIRED)
    if not minimal:
        values.extend(deepcopy(options.OPTIONAL))
    return dict(values)


def _pruned(iterable_to_prune):
    return iterable_to_prune[0] if len(iterable_to_prune) == 1 else iterable_to_prune
