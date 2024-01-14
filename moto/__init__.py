from moto.core.decorator import mock_aws  # noqa  # pylint: disable=unused-import

__title__ = "moto"
__version__ = "4.2.14.dev"


try:
    # Need to monkey-patch botocore requests back to underlying urllib3 classes
    from botocore.awsrequest import (  # type: ignore[attr-defined]
        HTTPConnection,
        HTTPConnectionPool,
        HTTPSConnectionPool,
        VerifiedHTTPSConnection,
    )
except ImportError:
    pass
else:
    HTTPSConnectionPool.ConnectionCls = VerifiedHTTPSConnection
    HTTPConnectionPool.ConnectionCls = HTTPConnection
