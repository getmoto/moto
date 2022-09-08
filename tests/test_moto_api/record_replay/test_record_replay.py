import boto3
import json
import requests
import sure  # noqa
from moto import settings, mock_apigateway, mock_dynamodb, mock_ec2, mock_timestreamwrite
from moto.core import DEFAULT_ACCOUNT_ID
from moto.moto_api._internal.record_replay import record_replay_api
from tests import EXAMPLE_AMI_ID
from unittest import SkipTest, TestCase


@mock_apigateway
@mock_dynamodb
@mock_ec2
@mock_timestreamwrite
class TestRecordServerMode(TestCase):

    def setUp(self) -> None:
        if not settings.TEST_SERVER_MODE:
            raise SkipTest("Can only test this in ServerMode")

        # turn recording off to ensure it's not bleeding over from other tests
        requests.post("http://localhost:5000/moto-api/record-replay/reset-recording")

    def test_ec2_instance_creation__recording_off(self):
        requests.post("http://localhost:5000/moto-api/record-replay/stop-recording")
        ec2 = boto3.client("ec2", region_name="us-west-1")
        ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

        resp = requests.get("http://localhost:5000/moto-api/record-replay/download-recording")
        resp.status_code.should.equal(200)
        resp.content.should.equal(b"")

    def test_ec2_instance_creation_recording_on(self):
        requests.post("http://localhost:5000/moto-api/record-replay/start-recording")
        ec2 = boto3.client("ec2", region_name="us-west-1")
        ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

        resp = requests.get("http://localhost:5000/moto-api/record-replay/download-recording")
        resp.status_code.should.equal(200)
        content = json.loads(resp.content)

        content.should.have.key("module").equals("moto.ec2.responses")
        content.should.have.key("response_type").should.equal("EC2Response")
        content.should.have.key("region").equals("us-west-1")
        content.should.have.key("querystring").should.have.key("Action").equals(["RunInstances"])
        content.should.have.key("querystring").should.have.key("ImageId").equals([EXAMPLE_AMI_ID])
        content.should.have.key("current_account").equals(DEFAULT_ACCOUNT_ID)

    def test_multiple_services(self):
        requests.post("http://localhost:5000/moto-api/record-replay/start-recording")
        ddb = boto3.client("dynamodb", "eu-west-1")
        ddb.create_table(
            TableName="test",
            AttributeDefinitions=[{"AttributeName": "client", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "client", "KeyType": "HASH"}],
            ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
        )
        ddb.put_item(TableName="test", Item={"client": {"S": "test1"}})

        ts = boto3.client("timestream-write", region_name="us-east-1")
        resp = ts.create_database(DatabaseName="mydatabase")

        apigw = boto3.client("apigateway", region_name="us-west-2")
        apigw.create_rest_api(name="my_api", description="desc")

        resp = requests.get("http://localhost:5000/moto-api/record-replay/download-recording")
        resp.status_code.should.equal(200)
        rows = [json.loads(x) for x in resp.content.splitlines()]

        rows.should.have.length_of(4)

        actions = [row["headers"].get("X-Amz-Target") for row in rows]
        actions.should.contain("DynamoDB_20120810.CreateTable")
        actions.should.contain("DynamoDB_20120810.PutItem")
        actions.should.contain("Timestream_20181101.CreateDatabase")

        hosts = set([row["headers"]["Host"] for row in rows])
        hosts.should.equal({'localhost:5000'})

        urls = set([row["url"] for row in rows])
        urls.should.equal({'http://localhost:5000/', 'http://localhost:5000/restapis'})


@mock_apigateway
@mock_dynamodb
@mock_ec2
@mock_timestreamwrite
class TestRecordDecoratorMode(TestCase):

    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("Will only test this using decorators")

        # turn recording off to ensure it's not bleeding over from other tests
        record_replay_api.reset_recording()

    def test_ec2_instance_creation__recording_off(self):
        ec2 = boto3.client("ec2", region_name="us-west-1")
        ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

        content = record_replay_api.download_recording()
        content.should.equal("")

    def test_ec2_instance_creation_recording_on(self):
        record_replay_api.start_recording()
        ec2 = boto3.client("ec2", region_name="us-west-1")
        ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

        content = record_replay_api.download_recording()
        content = json.loads(content)
        content.should.have.key("module").equals("moto.ec2.responses")
        content.should.have.key("response_type").should.equal("EC2Response")
        content.should.have.key("region").equals("us-west-1")
        content.should.have.key("body").match("Action=RunInstances")
        content.should.have.key("querystring").should.have.key("ImageId").equals([EXAMPLE_AMI_ID])
        content.should.have.key("current_account").equals(DEFAULT_ACCOUNT_ID)

    def test_multiple_services(self):
        record_replay_api.start_recording()
        ddb = boto3.client("dynamodb", "eu-west-1")
        ddb.create_table(
            TableName="test",
            AttributeDefinitions=[{"AttributeName": "client", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "client", "KeyType": "HASH"}],
            ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
        )
        ddb.put_item(TableName="test", Item={"client": {"S": "test1"}})

        ts = boto3.client("timestream-write", region_name="us-east-1")
        resp = ts.create_database(DatabaseName="mydatabase")

        apigw = boto3.client("apigateway", region_name="us-west-2")
        apigw.create_rest_api(name="my_api", description="desc")

        content = record_replay_api.download_recording()
        rows = [json.loads(x) for x in content.splitlines()]
        rows.should.have.length_of(5)

        actions = [row["headers"].get("X-Amz-Target") for row in rows]
        actions.should.contain("DynamoDB_20120810.CreateTable")
        actions.should.contain("DynamoDB_20120810.PutItem")
        actions.should.contain("Timestream_20181101.DescribeEndpoints")
        actions.should.contain("Timestream_20181101.CreateDatabase")

        hosts = set([row["headers"]["host"] for row in rows])
        hosts.should.equal({'ingest.timestream.us-east-1.amazonaws.com', 'apigateway.us-west-2.amazonaws.com', 'dynamodb.eu-west-1.amazonaws.com'})
