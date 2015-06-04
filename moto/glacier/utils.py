from six.moves.urllib.parse import urlparse


def region_from_glacier_url(url):
    domain = urlparse(url).netloc

    if '.' in domain:
        return domain.split(".")[1]
    else:
        return 'us-east-1'


def vault_from_glacier_url(full_url):
    return full_url.split("/")[-1]
