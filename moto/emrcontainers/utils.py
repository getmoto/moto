import json
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


# def paginated_list(full_list, max_results, next_token):
#     """
#     Returns a tuple containing a slice of the full list
#     starting at next_token and ending with at most the
#     max_results number of elements, and the new
#     next_token which can be passed back in for the next
#     segment of the full list.
#     """
#     # sorted_list = sorted(full_list)
#     list_len = len(full_list)
#
#     converted_list = [item.__dict__ for item in full_list]
#
#     start = converted_list.index(next_token) if next_token else 0
#     end = min(start + max_results, list_len)
#     new_next = None if end == list_len else full_list[end]
#
#     return converted_list[start:end], new_next
