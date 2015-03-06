from __future__ import unicode_literals
import boto

from moto import mock_sns


@mock_sns
def test_get_list_endpoints_by_platform_application():
    conn = boto.connect_sns()
    endpoint_list = conn.list_endpoints_by_platform_application(
        platform_application_arn='fake_arn'
    )['ListEndpointsByPlatformApplicationResponse']['ListEndpointsByPlatformApplicationResult']['Endpoints']

    endpoint_list.should.have.length_of(1)
    endpoint_list[0]['Attributes']['Enabled'].should.equal('true')
    endpoint_list[0]['EndpointArn'].should.equal('FAKE_ARN_ENDPOINT')
