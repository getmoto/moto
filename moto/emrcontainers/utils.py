# import json
import string
import random


def get_partition(region):
    valid_matches = [
        # (region prefix, aws partition)
        ("cn-", "aws-cn"),
        ("us-gov-", "aws-us-gov"),
        ("us-gov-iso-", "aws-iso"),
        ("us-gov-iso-b-", "aws-iso-b"),
    ]

    for prefix, partition in valid_matches:
        if region.startswith(prefix):
            return partition
    return "aws"


def random_id(size=13):
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def random_cluster_id(size=13):
    return random_id(size=25)


def paginated_list(full_list, max_results, next_token):
    """
    Returns a tuple containing a slice of the full list starting at next_token and ending with at most the max_results
    number of elements, and the new next_token which can be passed back in for the next segment of the full list.
    """
    if next_token is None or not next_token:
        next_token = 0
    next_token = int(next_token)

    sorted_list = sorted(full_list, key=lambda d: d["name"])

    values = sorted_list[next_token : next_token + max_results]
    if len(values) == max_results:
        new_next_token = str(next_token + max_results)
    else:
        new_next_token = None
    return values, new_next_token
