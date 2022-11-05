from moto.moto_api._internal import mock_random as random
import string


def vault_from_glacier_url(full_url):
    return full_url.split("/")[-1]


def get_job_id():
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(92)
    )
