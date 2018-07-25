from freezegun import freeze_time
import sure  # noqa

from tests.helpers import skip_in_server_mode
from moto.swf.models import Timeout

from ..utils import make_workflow_execution


@skip_in_server_mode
def test_timeout_creation():
    wfe = make_workflow_execution()

    # epoch 1420113600 == "2015-01-01 13:00:00"
    timeout = Timeout(wfe, 1420117200, "START_TO_CLOSE")

    with freeze_time("2015-01-01 12:00:00"):
        timeout.reached.should.be.falsy

    with freeze_time("2015-01-01 13:00:00"):
        timeout.reached.should.be.truthy
