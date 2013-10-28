import urlparse


def bucket_name_from_url(url):
    pth = urlparse.urlparse(url).path.lstrip("/")

    l = pth.lstrip("/").split("/")
    if len(l) == 0 or l[0] == "":
        return None
    return l[0]
