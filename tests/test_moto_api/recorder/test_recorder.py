import base64
import boto3
import json
import requests
import os
import sure  # noqa # pylint: disable=unused-import
from moto import (
    settings,
    mock_apigateway,
    mock_dynamodb,
    mock_ec2,
    mock_s3,
    mock_timestreamwrite,
)
from moto.moto_api import recorder
from moto.server import ThreadedMotoServer
from tests import EXAMPLE_AMI_ID
from unittest import SkipTest, TestCase


@mock_apigateway
@mock_dynamodb
@mock_ec2
@mock_s3
@mock_timestreamwrite
class TestRecorder(TestCase):
    def _reset_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/reset-recording")
        else:
            recorder.reset_recording()

    def _start_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/start-recording")
        else:
            recorder.start_recording()

    def _stop_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/stop-recording")
        else:
            recorder.stop_recording()

    def _download_recording(self):
        if settings.TEST_SERVER_MODE:
            resp = requests.get(
                "http://localhost:5000/moto-api/recorder/download-recording"
            )
            resp.status_code.should.equal(200)
            return resp.content
        else:
            return recorder.download_recording()

    def _replay_recording(self):
        if settings.TEST_SERVER_MODE:
            requests.post("http://localhost:5000/moto-api/recorder/replay-recording")
        else:
            recorder.replay_recording()

    def setUp(self) -> None:
        # Reset recorded calls to ensure it's not bleeding over from other tests
        self._reset_recording()

    def tearDown(self) -> None:
        self._stop_recording()

    def test_ec2_instance_creation__recording_off(self):
        ec2 = boto3.client(
            "ec2", "us-west-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

        self._download_recording().should.be.empty

    def test_ec2_instance_creation_recording_on(self):
        self._start_recording()
        ec2 = boto3.client(
            "ec2", "us-west-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)

        content = json.loads(self._download_recording())

        if content.get("body_encoded"):
            body = base64.b64decode(content.get("body")).decode("ascii")
        else:
            body = content["body"]

        body.should.contain("Action=RunInstances")
        body.should.contain(f"ImageId={EXAMPLE_AMI_ID}")

    def test_multiple_services(self):
        self._start_recording()
        ddb = boto3.client(
            "dynamodb", "eu-west-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        ddb.create_table(
            TableName="test",
            AttributeDefinitions=[{"AttributeName": "client", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "client", "KeyType": "HASH"}],
            ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
        )
        ddb.put_item(TableName="test", Item={"client": {"S": "test1"}})

        ts = boto3.client(
            "timestream-write",
            "us-east-1",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        ts.create_database(DatabaseName="mydatabase")

        apigw = boto3.client(
            "apigateway",
            "us-west-2",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        apigw.create_rest_api(name="my_api", description="desc")

        content = self._download_recording()
        rows = [json.loads(x) for x in content.splitlines()]

        actions = [row["headers"].get("X-Amz-Target") for row in rows]
        actions.should.contain("DynamoDB_20120810.CreateTable")
        actions.should.contain("DynamoDB_20120810.PutItem")
        actions.should.contain("Timestream_20181101.CreateDatabase")

    def test_replay(self):
        self._start_recording()
        ddb = boto3.client(
            "dynamodb", "eu-west-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        self._create_ddb_table(ddb, "test")

        apigw = boto3.client(
            "apigateway",
            "us-west-2",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        api_id = apigw.create_rest_api(name="my_api", description="desc")["id"]

        self._stop_recording()

        ddb.delete_table(TableName="test")
        apigw.delete_rest_api(restApiId=api_id)

        self._replay_recording()

        ddb.list_tables()["TableNames"].should.equal(["test"])

        apis = apigw.get_rest_apis()["items"]
        apis.should.have.length_of(1)
        # The ID is uniquely generated everytime, but the name is the same
        apis[0]["id"].shouldnt.equal(api_id)
        apis[0]["name"].should.equal("my_api")

    def test_replay__partial_delete(self):
        self._start_recording()
        ddb = boto3.client(
            "dynamodb", "eu-west-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        self._create_ddb_table(ddb, "test")

        apigw = boto3.client(
            "apigateway",
            "us-west-2",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        api_id = apigw.create_rest_api(name="my_api", description="desc")["id"]

        ddb.delete_table(TableName="test")
        self._stop_recording()

        apigw.delete_rest_api(restApiId=api_id)

        self._replay_recording()

        # The replay will create, then delete this Table
        ddb.list_tables()["TableNames"].should.equal([])

        # The replay will create the RestAPI - the deletion was not recorded
        apis = apigw.get_rest_apis()["items"]
        apis.should.have.length_of(1)

    def test_s3_upload_data(self):
        self._start_recording()
        s3 = boto3.client(
            "s3", "us-east-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        s3.create_bucket(Bucket="mybucket")
        s3.put_object(Bucket="mybucket", Body=b"ABCD", Key="data")

        self._stop_recording()
        s3.delete_object(Bucket="mybucket", Key="data")
        s3.delete_bucket(Bucket="mybucket")

        # Replaying should recreate the file as is
        self._replay_recording()
        resp = s3.get_object(Bucket="mybucket", Key="data")
        resp["Body"].read().should.equal(b"ABCD")

    def test_s3_upload_file_using_requests(self):
        s3 = boto3.client(
            "s3", "us-east-1", aws_access_key_id="ak", aws_secret_access_key="sk"
        )
        s3.create_bucket(Bucket="mybucket")

        params = {"Bucket": "mybucket", "Key": "file_upload"}
        _url = s3.generate_presigned_url("put_object", params, ExpiresIn=900)
        with open("text.txt", "w") as file:
            file.write("test")

        # Record file uploaded to S3 outside of boto3
        self._start_recording()
        requests.put(_url, files={"upload_file": open("text.txt", "rb")})
        self._stop_recording()

        # Delete file
        s3.delete_object(Bucket="mybucket", Key="file_upload")

        # Replay upload, and assert it succeeded
        self._replay_recording()
        resp = s3.get_object(Bucket="mybucket", Key="file_upload")
        resp["Body"].read().should.equal(b"test")
        # cleanup
        os.remove("text.txt")

    def _create_ddb_table(self, ddb, table_name):
        ddb.create_table(
            TableName=table_name,
            AttributeDefinitions=[{"AttributeName": "client", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "client", "KeyType": "HASH"}],
            ProvisionedThroughput={"ReadCapacityUnits": 123, "WriteCapacityUnits": 123},
        )


class TestThreadedMotoServer(TestCase):
    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("No point in testing ServerMode within ServerMode")

        self.port_1 = 5678
        self.port_2 = 5679
        # start server on port x
        server = ThreadedMotoServer(
            ip_address="127.0.0.1", port=self.port_1, verbose=False
        )
        server.start()
        requests.post(
            f"http://localhost:{self.port_1}/moto-api/recorder/reset-recording"
        )
        requests.post(
            f"http://localhost:{self.port_1}/moto-api/recorder/start-recording"
        )

        # create s3 file
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            endpoint_url=f"http://localhost:{self.port_1}",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        s3.create_bucket(Bucket="mybucket")
        s3.put_object(Bucket="mybucket", Body=b"ABCD", Key="data")

        # store content
        requests.post(
            f"http://localhost:{self.port_1}/moto-api/recorder/stop-recording"
        )
        self.content = requests.post(
            f"http://localhost:{self.port_1}/moto-api/recorder/download-recording"
        ).content
        server.stop()

    def test_server(self):
        # start motoserver on port y
        server = ThreadedMotoServer(
            ip_address="127.0.0.1", port=self.port_2, verbose=False
        )
        server.start()
        requests.post(f"http://localhost:{self.port_2}/moto-api/reset")
        # upload content
        requests.post(
            f"http://localhost:{self.port_2}/moto-api/recorder/upload-recording",
            data=self.content,
        )
        # replay
        requests.post(
            f"http://localhost:{self.port_2}/moto-api/recorder/replay-recording"
        )
        # assert the file exists
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            endpoint_url=f"http://localhost:{self.port_2}",
            aws_access_key_id="ak",
            aws_secret_access_key="sk",
        )
        resp = s3.get_object(Bucket="mybucket", Key="data")
        resp["Body"].read().should.equal(b"ABCD")
        server.stop()
