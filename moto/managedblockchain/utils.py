import random
import string

from six.moves.urllib.parse import urlparse


def region_from_managedblckchain_url(url):
    domain = urlparse(url).netloc

    if "." in domain:
        return domain.split(".")[1]
    else:
        return "us-east-1"


def networkid_from_managedblockchain_url(full_url):
    return full_url.split("/")[-1]


def get_network_id():
    return "n-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def get_member_id():
    return "m-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )
