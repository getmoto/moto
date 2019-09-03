import boto3
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_eb


@mock_eb
def test_create_application():
    # Create Elastic Beanstalk Application
    conn = boto3.client('elasticbeanstalk', region_name='us-east-1')
    app = conn.create_application(
        ApplicationName="myapp",
    )
    app['Application']['ApplicationName'].should.equal("myapp")


@mock_eb
def test_create_application_dup():
    conn = boto3.client('elasticbeanstalk', region_name='us-east-1')
    conn.create_application(
        ApplicationName="myapp",
    )
    conn.create_application.when.called_with(
        ApplicationName="myapp",
    ).should.throw(ClientError)


@mock_eb
def test_describe_applications():
    # Create Elastic Beanstalk Application
    conn = boto3.client('elasticbeanstalk', region_name='us-east-1')
    conn.create_application(
        ApplicationName="myapp",
    )

    apps = conn.describe_applications()
    len(apps['Applications']).should.equal(1)
    apps['Applications'][0]['ApplicationName'].should.equal('myapp')
