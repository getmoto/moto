import time

try:
    import urllib2 as urllib
    from urllib2 import URLError as ConnError
except ImportError:
    import urllib.request as urllib
    from urllib.error import URLError as ConnError


start_ts = time.time()
print("Waiting for service to come up")
while True:
    try:
        urllib.urlopen('http://localhost:5000/', timeout=1)
        break
    except (ConnError, ConnectionResetError):
        elapsed_s = time.time() - start_ts
        if elapsed_s > 30:
            raise

        print('.')
        time.sleep(1)
