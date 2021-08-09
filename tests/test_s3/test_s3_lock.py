import time
import boto3
import datetime
import botocore
from moto import mock_s3

import sure

@mock_s3
def test_locked_object_cycle():
    bucket_name = "locked-bucket-crist"
    key_name = "file.txt"
    seconds_lock = 5
    
    s3 = boto3.client("s3")

    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=False)
    try:
        s3.put_object(Bucket=bucket_name, Body=b"test", Key=key_name, 
            ObjectLockMode='COMPLIANCE', 
            ObjectLockLegalHoldStatus='ON')
    except botocore.client.ClientError as e:
        e.response['Error']['Code'].should.equal('InvalidArgument')

#     s3.delete_bucket(Bucket=bucket_name)
    s3.create_bucket(Bucket=bucket_name, ObjectLockEnabledForBucket=True)

    until = datetime.datetime.utcnow() + datetime.timedelta(0,seconds_lock)
    s3.put_object(Bucket=bucket_name, Body=b"test", Key="file.txt", 
        ObjectLockMode='COMPLIANCE',
        ObjectLockRetainUntilDate=until)

    versions_response = s3.list_object_versions(Bucket=bucket_name)
    version_id = versions_response['Versions'][0]['VersionId']

    try:
        s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
    except botocore.client.ClientError as e:
        e.response['Error']['Code'].should.equal('AccessDenied')
    
    #cleaning
    time.sleep(seconds_lock)
    s3.delete_object(Bucket=bucket_name, Key=key_name, VersionId=version_id)
    s3.delete_bucket(Bucket=bucket_name)

 