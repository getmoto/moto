import os
import time

import urllib.request as urllib
from urllib.error import URLError
import socket

EXCEPTIONS = (URLError, socket.timeout, ConnectionResetError)


start_ts = time.time()
expected_port = os.environ.get("MOTO_PORT", "5000")
expected_host = "http://localhost:{}/".format(expected_port)
print("Waiting for service to come up on {}".format(expected_host))
while True:
    try:

        urllib.urlopen(expected_host, timeout=1)
        break
    except EXCEPTIONS:
        elapsed_s = time.time() - start_ts
        if elapsed_s > 120:
            raise

        print(".")
        time.sleep(1)
