from urllib.parse import urlparse


def bucket_name_from_url(url):
    path = urlparse(url).path.lstrip("/")

    parts = path.lstrip("/").split("/")
    if len(parts) == 0 or parts[0] == "":
        return None
    return parts[0]


def parse_key_name(path):
    return "/".join(path.split("/")[2:])
