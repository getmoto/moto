import boto3
from moto import mock_eb


@mock_eb
def test_application():
    # Create Elastic Beanstalk Application
    eb_client = boto3.client('elasticbeanstalk', region_name='us-east-1')

    eb_client.create_application(
        ApplicationName="myapp",
    )

    eb_apps = eb_client.describe_applications()
    eb_apps['Applications'][0]['ApplicationName'].should.equal("myapp")
