from moto import mock_secretsmanager
import boto3
from pprint import pprint as print
import pdb
@mock_secretsmanager
def test_my_model_save():
    service_client = boto3.client('secretsmanager')
    resp = service_client.create_secret(Name="testsecret", SecretString='test1')
    secret_arn = resp['Name']

    #service_client.get_secret_value(SecretId=secret_arn, VersionStage='AWSCURRENT')
    #service_client.list_secret_version_ids(SecretId=secret_arn)
    #service_client.describe_secret(SecretId=secret_arn)


    print('rotate secret')
    service_client.get_secret_value(SecretId=secret_arn, VersionStage='AWSCURRENT')
    service_client.rotate_secret(SecretId=secret_arn)
    service_client.get_secret_value(SecretId=secret_arn, VersionStage='AWSCURRENT')

test_my_model_save()