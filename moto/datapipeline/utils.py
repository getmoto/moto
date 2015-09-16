from moto.core.utils import get_random_hex


def get_random_pipeline_id():
    return "df-{0}".format(get_random_hex(length=19))
