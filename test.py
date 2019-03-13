from moto import mock_secretsmanager
import boto3
import pdb
@mock_secretsmanager
def test_my_model_save():
    service_client = boto3.client('secretsmanager')
    resp = service_client.create_secret(Name="testsecret", SecretString='test1')
    secret_arn = resp['ARN']

    print(0)
    print(service_client.put_secret_value(SecretId=secret_arn, SecretString='test2'))
    print(1)
    print(service_client.get_secret_value(SecretId=secret_arn, VersionId='AWSCURRENT'))

test_my_model_save()