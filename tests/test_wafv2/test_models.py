import random
import string

from moto.wafv2.models import WebACL


def test_webacl_class_defaults():
    wacl = WebACL()
    assert wacl.ARN.startswith("arn:aws:wafv2:us-east-1:123456789012:regional/webacl/Mock-WebACL-name-")
    assert wacl.Name.startswith("Mock-WebACL-name-")
    assert wacl.DefaultAction == {"Allow": {}}
    assert wacl.VisibilityConfig.MetricName.startswith("Mock-WebACL-name-")
    assert wacl.VisibilityConfig.SampledRequestsEnabled is True
    assert wacl.VisibilityConfig.CloudWatchMetricsEnabled is False
    assert len(wacl.Id) == 36


def test_wacl_name_length_limit_128():
    longname = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(150))
    assert len(longname) > 128
    wacl = WebACL(longname)
    assert len(wacl.Name) == 128


def test_webacl_to_dict():
    wacl_dict = WebACL().to_dict()
    assert wacl_dict['ARN'].startswith("arn:aws:wafv2:us-east-1:123456789012:regional/webacl/Mock-WebACL-name-")
    assert wacl_dict['Name'].startswith("Mock-WebACL-name-")
    visibility_config = wacl_dict['VisibilityConfig']
    assert visibility_config["SampledRequestsEnabled"] is True
    assert visibility_config["CloudWatchMetricsEnabled"] is False
    assert visibility_config["MetricName"] == wacl_dict['Name']
