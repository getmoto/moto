import sure  # noqa # pylint: disable=unused-import
import xmltodict

import moto.server as server
from tests import DEFAULT_ACCOUNT_ID


def test_cloudfront_list():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="cloudfront"
    )
    test_client = backend.test_client()

    res = test_client.get("/2020-05-31/distribution")
    data = xmltodict.parse(res.data, dict_constructor=dict)
    data.should.have.key("DistributionList")
    data["DistributionList"].shouldnt.have.key("Items")
