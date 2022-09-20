import boto3
import uuid
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError
from moto import mock_cognitoidp, mock_iam
from moto.moto_api import mock_random, recorder


@mock_cognitoidp
@mock_iam
def test_create_user_pool_using_preset_seed():
    conn = boto3.client("cognito-idp", "us-west-2")

    random_seed = 42

    # start recording
    recorder.reset_recording()
    recorder.start_recording()
    # Create UserPool
    name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    mock_random.seed(random_seed)
    pool_id = conn.create_user_pool(PoolName=name, LambdaConfig={"PreSignUp": value})[
        "UserPool"
    ]["Id"]

    # stop recording
    recorder.stop_recording()

    # set seed to same number
    mock_random.seed(random_seed)
    # delete user pool
    conn.delete_user_pool(UserPoolId=pool_id)
    # replay recording
    recorder.replay_recording()
    # assert userpool is is the same - it will throw an error if it doesn't exist
    conn.describe_user_pool(UserPoolId=pool_id)
    # delete user pool
    conn.delete_user_pool(UserPoolId=pool_id)

    # set seed to different number
    mock_random.seed(random_seed + 1)
    # replay recording, and recreate a userpool
    recorder.replay_recording()
    # assert the ID of this userpool is now different
    with pytest.raises(ClientError) as exc:
        conn.describe_user_pool(UserPoolId=pool_id)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")

    all_pools = conn.list_user_pools(MaxResults=5)["UserPools"]
    all_pools.should.have.length_of(1)
