import time

try:
    # py2
    import urllib2 as urllib
    from urllib2 import URLError
    import socket
    import httplib

    EXCEPTIONS = (URLError, socket.error, httplib.BadStatusLine)
except ImportError:
    # py3
    import urllib.request as urllib
    from urllib.error import URLError
    import socket

    EXCEPTIONS = (URLError, socket.timeout, ConnectionResetError)


start_ts = time.time()
print("Waiting for service to come up")
while True:
    try:
        urllib.urlopen('http://localhost:5000/', timeout=1)
        break
    except EXCEPTIONS:
        elapsed_s = time.time() - start_ts
        if elapsed_s > 60:
            raise

        print('.')
        time.sleep(1)
