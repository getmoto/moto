import random
import re
import string

from six.moves.urllib.parse import urlparse


def region_from_managedblckchain_url(url):
    domain = urlparse(url).netloc

    if "." in domain:
        return domain.split(".")[1]
    else:
        return "us-east-1"


def networkid_from_managedblockchain_url(full_url):
    id_search = re.search("n-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0)
    return return_id


def get_network_id():
    return "n-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def memberid_from_managedblockchain_url(full_url):
    id_search = re.search("m-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0)
    return return_id


def get_member_id():
    return "m-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def proposalid_from_managedblockchain_url(full_url):
    id_search = re.search("p-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0)
    return return_id


def get_proposal_id():
    return "p-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )
