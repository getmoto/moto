from unittest import SkipTest

import requests

from moto import settings

url = "http://motoapi.amazonaws.com/moto-api/proxy/passthrough"


def test_real_request_errors() -> None:
    if not settings.is_test_proxy_mode():
        raise SkipTest("Can only be tested in ProxyMode")

    http_proxy = settings.test_proxy_mode_endpoint()
    https_proxy = settings.test_proxy_mode_endpoint()
    proxies = {"http": http_proxy, "https": https_proxy}

    # Delete all to ensure we're starting with a clean slate
    requests.delete(url, proxies=proxies)

    resp = requests.get("http://httpbin.org/robots.txt", proxies=proxies)
    assert resp.status_code == 404
    assert resp.content == b"AWS Service not recognized or supported"


def test_configure_passedthrough_urls() -> None:
    if not settings.is_test_proxy_mode():
        raise SkipTest("Can only be tested in ProxyMode")

    http_proxy = settings.test_proxy_mode_endpoint()
    https_proxy = settings.test_proxy_mode_endpoint()
    proxies = {"http": http_proxy, "https": https_proxy}

    # Delete all to ensure we're starting with a clean slate
    requests.delete(url, proxies=proxies)

    target1 = "http://httpbin.org/robots.txt"
    target2 = "http://othersite.org/"
    target3 = "https://othersite.org/"
    resp = requests.post(url, json={"http_urls": [target1]}, proxies=proxies)
    assert resp.status_code == 201
    assert resp.json() == {"http_urls": [target1], "https_hosts": []}

    # We can configure multiple URL's
    resp = requests.post(url, json={"http_urls": [target2]}, proxies=proxies)
    assert target1 in resp.json()["http_urls"]
    assert target2 in resp.json()["http_urls"]

    # Duplicate URL's are ignored
    requests.post(url, json={"http_urls": [target1]}, proxies=proxies)

    # We can retrieve the data
    resp = requests.get(url, proxies=proxies)
    assert target1 in resp.json()["http_urls"]
    assert target2 in resp.json()["http_urls"]
    assert resp.json()["https_hosts"] == []

    # Set HTTPS HOST for good measure
    resp = requests.post(url, json={"https_hosts": [target3]}, proxies=proxies)
    assert target1 in resp.json()["http_urls"]
    assert target2 in resp.json()["http_urls"]
    assert resp.json()["https_hosts"] == [target3]

    # We can delete all URL's in one go
    requests.delete(url, proxies=proxies)

    resp = requests.get(url, proxies=proxies)
    assert resp.json() == {"http_urls": [], "https_hosts": []}


def test_http_get_request_can_be_passed_through() -> None:
    if not settings.is_test_proxy_mode():
        raise SkipTest("Can only be tested in ProxyMode")

    http_proxy = settings.test_proxy_mode_endpoint()
    https_proxy = settings.test_proxy_mode_endpoint()
    proxies = {"http": http_proxy, "https": https_proxy}

    # Delete all to ensure we're starting with a clean slate
    requests.delete(url, proxies=proxies)

    # Configure our URL as the one to passthrough
    target_url = "http://httpbin.org/robots.txt"
    requests.post(url, json={"http_urls": [target_url]}, proxies=proxies)

    resp = requests.get("http://httpbin.org/robots.txt", proxies=proxies)
    assert resp.status_code == 200
    assert b"/deny" in resp.content


def test_http_post_request_can_be_passed_through() -> None:
    if not settings.is_test_proxy_mode():
        raise SkipTest("Can only be tested in ProxyMode")

    http_proxy = settings.test_proxy_mode_endpoint()
    https_proxy = settings.test_proxy_mode_endpoint()
    proxies = {"http": http_proxy, "https": https_proxy}

    # Delete all to ensure we're starting with a clean slate
    requests.delete(url, proxies=proxies)

    # Configure our URL as the one to passthrough
    target_url = "http://httpbin.org/response-headers?x-moto-test=someval"
    requests.post(url, json={"http_urls": [target_url]}, proxies=proxies)

    resp = requests.post(target_url, proxies=proxies)
    assert "x-moto-test" in resp.json()


def test_https_request_can_be_passed_through() -> None:
    if not settings.is_test_proxy_mode():
        raise SkipTest("Can only be tested in ProxyMode")

    http_proxy = settings.test_proxy_mode_endpoint()
    https_proxy = settings.test_proxy_mode_endpoint()
    proxies = {"http": http_proxy, "https": https_proxy}

    # Delete all to ensure we're starting with a clean slate
    requests.delete(url, proxies=proxies)

    # Configure our URL as the one to passthrough
    target_url = "https://httpbin.org/ip"
    requests.post(url, json={"https_hosts": ["httpbin.org"]}, proxies=proxies)

    resp = requests.get(target_url, proxies=proxies)
    assert resp.status_code == 200
    assert "origin" in resp.json()
