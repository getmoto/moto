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


@mock_eb
def test_create_environment():
    # Create Elastic Beanstalk Environment
    conn = boto3.client('elasticbeanstalk', region_name='us-east-1')
    app = conn.create_application(
        ApplicationName="myapp",
    )
    env = conn.create_environment(
        ApplicationName="myapp",
        EnvironmentName="myenv",
    )
    env['EnvironmentName'].should.equal("myenv")


@mock_eb
def test_describe_environments():
    # List Elastic Beanstalk Envs
    conn = boto3.client('elasticbeanstalk', region_name='us-east-1')
    conn.create_application(
        ApplicationName="myapp",
    )
    conn.create_environment(
        ApplicationName="myapp",
        EnvironmentName="myenv",
    )

    envs = conn.describe_environments()
    envs = envs['Environments']
    len(envs).should.equal(1)
    envs[0]['ApplicationName'].should.equal('myapp')
    envs[0]['EnvironmentName'].should.equal('myenv')


@mock_eb
def test_list_available_solution_stacks():
    conn = boto3.client('elasticbeanstalk', region_name='us-east-1')
    stacks = conn.list_available_solution_stacks()
    len(stacks['SolutionStacks']).should.be.greater_than(0)
    len(stacks['SolutionStacks']).should.be.equal(len(stacks['SolutionStackDetails']))
