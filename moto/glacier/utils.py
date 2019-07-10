import random
import string

from six.moves.urllib.parse import urlparse


def region_from_glacier_url(url):
    domain = urlparse(url).netloc

    if "." in domain:
        return domain.split(".")[1]
    else:
        return "us-east-1"


def vault_from_glacier_url(full_url):
    return full_url.split("/")[-1]


def get_job_id():
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(92)
    )
