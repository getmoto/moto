from copy import deepcopy
from random import randint

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from moto.utilities.utils import random_string
from tests.test_eks.test_eks_constants import (
    ClusterAttributes,
    ClusterInputs,
    NodegroupAttributes,
    NodegroupInputs,
    ResponseAttributes,
    STATUS,
)

generate_random_name = random_string


def attributes_to_test(inputs, name):
    """
    Assembles the list of tuples which will be used to validate test results.
    """
    result = deepcopy(inputs.REQUIRED + inputs.OPTIONAL + [STATUS])
    if isinstance(inputs, ClusterInputs):
        result += [(ClusterAttributes.NAME, name)]
    elif isinstance(inputs, NodegroupInputs):
        result += [(NodegroupAttributes.NODEGROUP_NAME, name)]

    return result


def generate_clusters(client, num_clusters, minimal):
    """
    Generates 'num_clusters' number of clusters with randomized data and adds them to the mocked backend.
    If 'minimal' is True, only the required values are generated; if False all values are generated.
    Returns a list of the names of the generated clusters.
    """
    return [
        client.create_cluster(
            name=generate_random_name(), **_input_builder(ClusterInputs, minimal)
        )[ResponseAttributes.CLUSTER][ClusterAttributes.NAME]
        for _ in range(num_clusters)
    ]


def generate_nodegroups(client, cluster_name, num_nodegroups, minimal):
    """
    Generates 'num_nodegroups' number of nodegroups with randomized data and adds them to the mocked backend.
    If 'minimal' is True, only the required values are generated; if False, all values are generated.
    Returns a list of the names of the generated nodegroups.
    """
    return [
        client.create_nodegroup(
            nodegroupName=generate_random_name(),
            clusterName=cluster_name,
            **_input_builder(NodegroupInputs, minimal)
        )[ResponseAttributes.NODEGROUP][NodegroupAttributes.NODEGROUP_NAME]
        for _ in range(num_nodegroups)
    ]


def is_valid_uri(value):
    """
    Returns true if a provided string has the form of a valid uri.
    """
    result = urlparse(value)
    return all([result.scheme, result.netloc, result.path])


def region_matches_partition(region, partition):
    """
    Returns True if the provided region and partition are a valid pair.
    """
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
    """
    Assembles the inputs which will be used to generate test object into a dictionary.
    """
    values = deepcopy(options.REQUIRED)
    if not minimal:
        values.extend(deepcopy(options.OPTIONAL))
    return dict(values)


def random_names(name_list):
    """
    Returns one value picked at random a list, and one value guaranteed not to be on the list.
    """
    name_on_list = name_list[randint(0, len(name_list) - 1)]

    name_not_on_list = generate_random_name()
    while name_not_on_list in name_list:
        name_not_on_list = generate_random_name()

    return name_on_list, name_not_on_list
