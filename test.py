from moto import mock_secretsmanager
import boto3
import pdb
@mock_secretsmanager
def test_my_model_save():
    service_client = boto3.client('secretsmanager')
    resp = service_client.create_secret(Name="testsecret", SecretString='test1')
    secret_arn = resp['Name']


    print(0)
    print(service_client.put_secret_value(SecretId=secret_arn, SecretString='test2', VersionStages=['AWSCURRENT']))
    print(1)
    print(service_client.get_secret_value(SecretId=secret_arn, VersionStage='AWSCURRENT'))
    print(2)
    print(service_client.list_secret_version_ids(SecretId=secret_arn))
    print(3)
    print(service_client.describe_secret(SecretId=secret_arn))

test_my_model_save()