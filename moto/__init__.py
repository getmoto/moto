from __future__ import unicode_literals
# import logging
# logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = 'moto'
__version__ = '1.3.14.dev'


try:
    # Need to monkey-patch botocore requests back to underlying urllib3 classes
    from botocore.awsrequest import HTTPSConnectionPool, HTTPConnectionPool, HTTPConnection, VerifiedHTTPSConnection
except ImportError:
    pass
else:
    HTTPSConnectionPool.ConnectionCls = VerifiedHTTPSConnection
    HTTPConnectionPool.ConnectionCls = HTTPConnection
