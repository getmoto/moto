"""AWS cfnresponse Lambda script."""

# Modified version of the official AWS cfnresponse-module

import json
import socket
import urllib3


SUCCESS = "SUCCESS"
FAILED = "FAILED"


def send(
    event,
    context,
    response_status,
    response_data,
    physical_resource_id=None,
    no_echo=False,
):  # pylint: disable=too-many-arguments
    """Send function."""
    response_url = event["ResponseURL"]

    response_body = dict()
    response_body["Status"] = response_status
    response_body["Reason"] = (
        "See the details in CloudWatch Log Stream: " + context.log_stream_name
    )
    response_body["PhysicalResourceId"] = (
        physical_resource_id or context.log_stream_name
    )
    response_body["StackId"] = event["StackId"]
    response_body["RequestId"] = event["RequestId"]
    response_body["LogicalResourceId"] = event["LogicalResourceId"]
    response_body["NoEcho"] = no_echo
    response_body["Data"] = response_data

    json_response_body = json.dumps(response_body)

    debug()

    # send_request(url=response_url, data=json_response_body)

    urllib_request(response_url, response_body)


def debug():
    try:
        import requests

        print(requests)
    except ImportError:
        print("No module requests available")

    print(f"Is Docker: {is_docker()}")


def is_docker():
    import os

    path = "/proc/self/cgroup"
    return (
        os.path.exists("/.dockerenv")
        or os.path.isfile(path)
        and any("docker" in line for line in open(path))
    )


def urllib_request(url, data):
    http = urllib3.PoolManager()

    encoded_data = json.dumps(data).encode("utf-8")

    http.request("POST", url, body=encoded_data)


def send_request(url, data):
    # Ideally we use requests.put - but we may not have access to requests-module
    # So let's do it the old-fashioned way
    host, port, path = get_host_port_path(url)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect the client
    print(f"Connecting to ({host}, {port})...")
    client.connect((host, int(port)))

    # send some data
    payload = create_payload(host, port, path, data)
    client.sendall(payload)
    client.shutdown(socket.SHUT_RDWR)
    client.close()


def get_host_port_path(url):
    # Deconstruct url into host, port, path
    # http://localhost:5000/path --> http://localhost, 5000, /path
    #
    # Ignore the first characters if the URL starts with protocol
    ignore_first = 8 if url.startswith("http://") or url.startswith("https://") else 0
    host = url[0 : url.index(":", ignore_first)]
    port = url[url.index(":", ignore_first) + 1 : url.index("/", ignore_first)]
    path = url[url.index("/", ignore_first) :]
    return host, port, path


def create_payload(host, port, path, body):
    headers = """\
POST /{path} HTTP/1.1\r
Content-Type: {content_type}\r
Content-Length: {content_length}\r
Host: {host}\r
Connection: close\r
\r\n"""

    body_bytes = body.encode("ascii")
    header_bytes = headers.format(
        path=path,
        content_type="",
        content_length=len(body_bytes),
        host=str(host) + ":" + str(port),
    ).encode("iso-8859-1")

    return header_bytes + body_bytes
