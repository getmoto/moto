import sure  # flake8: noqa

import moto.server as server

'''
Test the different server responses
'''
server.configure_urls("autoscaling")


def test_describe_autoscaling_groups():
    test_client = server.app.test_client()
    res = test_client.get('/?Action=DescribeLaunchConfigurations')

    res.data.should.contain('<DescribeLaunchConfigurationsResponse')
    res.data.should.contain('<LaunchConfigurations>')
