from copy import deepcopy
from urllib.parse import urlparse

from moto.utilities.utils import random_string
from tests.test_eks.test_eks_constants import ClusterInputs, ClusterAttribute


def generate_clusters(client, num_clusters, minimal):
    input_values = deepcopy(ClusterInputs.REQUIRED)
    if not minimal:
        input_values.extend(deepcopy(ClusterInputs.OPTIONAL))

    cluster_names = [
        client.create_cluster(name=random_string(), **dict(input_values))[
            ClusterAttribute.CLUSTER
        ][ClusterAttribute.NAME]
        for _ in range(num_clusters)
    ]

    return cluster_names[0] if num_clusters == 1 else cluster_names


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
