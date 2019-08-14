from __future__ import unicode_literals
import os, re
import boto3
import boto.kms
import botocore.exceptions
from boto.exception import JSONResponseError
from boto.kms.exceptions import AlreadyExistsException, NotFoundException

from moto.kms.exceptions import NotFoundException as MotoNotFoundException
import sure  # noqa
from moto import mock_kms, mock_kms_deprecated
from nose.tools import assert_raises
from freezegun import freeze_time
from datetime import date
from datetime import datetime
from dateutil.tz import tzutc


@mock_kms
def test_create_key():
    conn = boto3.client('kms', region_name='us-east-1')
    with freeze_time("2015-01-01 00:00:00"):
        key = conn.create_key(Policy="my policy",
                              Description="my key",
                              KeyUsage='ENCRYPT_DECRYPT',
                              Tags=[
                                  {
                                      'TagKey': 'project',
                                      'TagValue': 'moto',
                                  },
                              ])

        key['KeyMetadata']['Description'].should.equal("my key")
        key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")
        key['KeyMetadata']['Enabled'].should.equal(True)
        key['KeyMetadata']['CreationDate'].should.be.a(date)


@mock_kms_deprecated
def test_describe_key():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    key = conn.describe_key(key_id)
    key['KeyMetadata']['Description'].should.equal("my key")
    key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")


@mock_kms_deprecated
def test_describe_key_via_alias():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    conn.create_alias(alias_name='alias/my-key-alias',
                      target_key_id=key['KeyMetadata']['KeyId'])

    alias_key = conn.describe_key('alias/my-key-alias')
    alias_key['KeyMetadata']['Description'].should.equal("my key")
    alias_key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")
    alias_key['KeyMetadata']['Arn'].should.equal(key['KeyMetadata']['Arn'])


@mock_kms_deprecated
def test_describe_key_via_alias_not_found():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    conn.create_alias(alias_name='alias/my-key-alias',
                      target_key_id=key['KeyMetadata']['KeyId'])

    conn.describe_key.when.called_with(
        'alias/not-found-alias').should.throw(JSONResponseError)


@mock_kms_deprecated
def test_describe_key_via_arn():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    arn = key['KeyMetadata']['Arn']

    the_key = conn.describe_key(arn)
    the_key['KeyMetadata']['Description'].should.equal("my key")
    the_key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")
    the_key['KeyMetadata']['KeyId'].should.equal(key['KeyMetadata']['KeyId'])


@mock_kms_deprecated
def test_describe_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.describe_key.when.called_with(
        "not-a-key").should.throw(JSONResponseError)


@mock_kms_deprecated
def test_list_keys():
    conn = boto.kms.connect_to_region("us-west-2")

    conn.create_key(policy="my policy", description="my key1",
                    key_usage='ENCRYPT_DECRYPT')
    conn.create_key(policy="my policy", description="my key2",
                    key_usage='ENCRYPT_DECRYPT')

    keys = conn.list_keys()
    keys['Keys'].should.have.length_of(2)


@mock_kms_deprecated
def test_enable_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.enable_key_rotation(key_id)

    conn.get_key_rotation_status(
        key_id)['KeyRotationEnabled'].should.equal(True)


@mock_kms_deprecated
def test_enable_key_rotation_via_arn():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['Arn']

    conn.enable_key_rotation(key_id)

    conn.get_key_rotation_status(
        key_id)['KeyRotationEnabled'].should.equal(True)


@mock_kms_deprecated
def test_enable_key_rotation_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.enable_key_rotation.when.called_with(
        "not-a-key").should.throw(NotFoundException)


@mock_kms_deprecated
def test_enable_key_rotation_with_alias_name_should_fail():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    conn.create_alias(alias_name='alias/my-key-alias',
                      target_key_id=key['KeyMetadata']['KeyId'])

    alias_key = conn.describe_key('alias/my-key-alias')
    alias_key['KeyMetadata']['Arn'].should.equal(key['KeyMetadata']['Arn'])

    conn.enable_key_rotation.when.called_with(
        'alias/my-alias').should.throw(NotFoundException)


@mock_kms_deprecated
def test_disable_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.enable_key_rotation(key_id)
    conn.get_key_rotation_status(
        key_id)['KeyRotationEnabled'].should.equal(True)

    conn.disable_key_rotation(key_id)
    conn.get_key_rotation_status(
        key_id)['KeyRotationEnabled'].should.equal(False)


@mock_kms_deprecated
def test_encrypt():
    """
    test_encrypt
    Using base64 encoding to merely test that the endpoint was called
    """
    conn = boto.kms.connect_to_region("us-west-2")
    response = conn.encrypt('key_id', 'encryptme'.encode('utf-8'))
    response['CiphertextBlob'].should.equal(b'ZW5jcnlwdG1l')
    response['KeyId'].should.equal('key_id')


@mock_kms_deprecated
def test_decrypt():
    conn = boto.kms.connect_to_region('us-west-2')
    response = conn.decrypt('ZW5jcnlwdG1l'.encode('utf-8'))
    response['Plaintext'].should.equal(b'encryptme')
    response['KeyId'].should.equal('key_id')


@mock_kms_deprecated
def test_disable_key_rotation_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.disable_key_rotation.when.called_with(
        "not-a-key").should.throw(NotFoundException)


@mock_kms_deprecated
def test_get_key_rotation_status_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.get_key_rotation_status.when.called_with(
        "not-a-key").should.throw(NotFoundException)


@mock_kms_deprecated
def test_get_key_rotation_status():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.get_key_rotation_status(
        key_id)['KeyRotationEnabled'].should.equal(False)


@mock_kms_deprecated
def test_create_key_defaults_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy",
                          description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.get_key_rotation_status(
        key_id)['KeyRotationEnabled'].should.equal(False)


@mock_kms_deprecated
def test_get_key_policy():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    policy = conn.get_key_policy(key_id, 'default')
    policy['Policy'].should.equal('my policy')


@mock_kms_deprecated
def test_get_key_policy_via_arn():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    policy = conn.get_key_policy(key['KeyMetadata']['Arn'], 'default')

    policy['Policy'].should.equal('my policy')


@mock_kms_deprecated
def test_put_key_policy():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.put_key_policy(key_id, 'default', 'new policy')
    policy = conn.get_key_policy(key_id, 'default')
    policy['Policy'].should.equal('new policy')


@mock_kms_deprecated
def test_put_key_policy_via_arn():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['Arn']

    conn.put_key_policy(key_id, 'default', 'new policy')
    policy = conn.get_key_policy(key_id, 'default')
    policy['Policy'].should.equal('new policy')


@mock_kms_deprecated
def test_put_key_policy_via_alias_should_not_update():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    conn.create_alias(alias_name='alias/my-key-alias',
                      target_key_id=key['KeyMetadata']['KeyId'])

    conn.put_key_policy.when.called_with(
        'alias/my-key-alias', 'default', 'new policy').should.throw(NotFoundException)

    policy = conn.get_key_policy(key['KeyMetadata']['KeyId'], 'default')
    policy['Policy'].should.equal('my policy')


@mock_kms_deprecated
def test_put_key_policy():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    conn.put_key_policy(key['KeyMetadata']['Arn'], 'default', 'new policy')

    policy = conn.get_key_policy(key['KeyMetadata']['KeyId'], 'default')
    policy['Policy'].should.equal('new policy')


@mock_kms_deprecated
def test_list_key_policies():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy',
                          description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    policies = conn.list_key_policies(key_id)
    policies['PolicyNames'].should.equal(['default'])


@mock_kms_deprecated
def test__create_alias__returns_none_if_correct():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    resp = kms.create_alias('alias/my-alias', key_id)

    resp.should.be.none


@mock_kms_deprecated
def test__create_alias__raises_if_reserved_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    reserved_aliases = [
        'alias/aws/ebs',
        'alias/aws/s3',
        'alias/aws/redshift',
        'alias/aws/rds',
    ]

    for alias_name in reserved_aliases:
        with assert_raises(JSONResponseError) as err:
            kms.create_alias(alias_name, key_id)

        ex = err.exception
        ex.error_message.should.be.none
        ex.error_code.should.equal('NotAuthorizedException')
        ex.body.should.equal({'__type': 'NotAuthorizedException'})
        ex.reason.should.equal('Bad Request')
        ex.status.should.equal(400)


@mock_kms_deprecated
def test__create_alias__can_create_multiple_aliases_for_same_key_id():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    kms.create_alias('alias/my-alias3', key_id).should.be.none
    kms.create_alias('alias/my-alias4', key_id).should.be.none
    kms.create_alias('alias/my-alias5', key_id).should.be.none


@mock_kms_deprecated
def test__create_alias__raises_if_wrong_prefix():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    with assert_raises(JSONResponseError) as err:
        kms.create_alias('wrongprefix/my-alias', key_id)

    ex = err.exception
    ex.error_message.should.equal('Invalid identifier')
    ex.error_code.should.equal('ValidationException')
    ex.body.should.equal({'message': 'Invalid identifier',
                          '__type': 'ValidationException'})
    ex.reason.should.equal('Bad Request')
    ex.status.should.equal(400)


@mock_kms_deprecated
def test__create_alias__raises_if_duplicate():
    region = 'us-west-2'
    kms = boto.kms.connect_to_region(region)
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']
    alias = 'alias/my-alias'

    kms.create_alias(alias, key_id)

    with assert_raises(AlreadyExistsException) as err:
        kms.create_alias(alias, key_id)

    ex = err.exception
    ex.error_message.should.match(r'An alias with the name arn:aws:kms:{region}:\d{{12}}:{alias} already exists'
                                  .format(**locals()))
    ex.error_code.should.be.none
    ex.box_usage.should.be.none
    ex.request_id.should.be.none
    ex.body['message'].should.match(r'An alias with the name arn:aws:kms:{region}:\d{{12}}:{alias} already exists'
                                    .format(**locals()))
    ex.body['__type'].should.equal('AlreadyExistsException')
    ex.reason.should.equal('Bad Request')
    ex.status.should.equal(400)


@mock_kms_deprecated
def test__create_alias__raises_if_alias_has_restricted_characters():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    alias_names_with_restricted_characters = [
        'alias/my-alias!',
        'alias/my-alias$',
        'alias/my-alias@',
    ]

    for alias_name in alias_names_with_restricted_characters:
        with assert_raises(JSONResponseError) as err:
            kms.create_alias(alias_name, key_id)
        ex = err.exception
        ex.body['__type'].should.equal('ValidationException')
        ex.body['message'].should.equal(
            "1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$".format(**locals()))
        ex.error_code.should.equal('ValidationException')
        ex.message.should.equal(
            "1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$".format(**locals()))
        ex.reason.should.equal('Bad Request')
        ex.status.should.equal(400)


@mock_kms_deprecated
def test__create_alias__raises_if_alias_has_colon_character():
    # For some reason, colons are not accepted for an alias, even though they
    # are accepted by regex ^[a-zA-Z0-9:/_-]+$
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    alias_names_with_restricted_characters = [
        'alias/my:alias',
    ]

    for alias_name in alias_names_with_restricted_characters:
        with assert_raises(JSONResponseError) as err:
            kms.create_alias(alias_name, key_id)
        ex = err.exception
        ex.body['__type'].should.equal('ValidationException')
        ex.body['message'].should.equal(
            "{alias_name} contains invalid characters for an alias".format(**locals()))
        ex.error_code.should.equal('ValidationException')
        ex.message.should.equal(
            "{alias_name} contains invalid characters for an alias".format(**locals()))
        ex.reason.should.equal('Bad Request')
        ex.status.should.equal(400)


@mock_kms_deprecated
def test__create_alias__accepted_characters():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    alias_names_with_accepted_characters = [
        'alias/my-alias_/',
        'alias/my_alias-/',
    ]

    for alias_name in alias_names_with_accepted_characters:
        kms.create_alias(alias_name, key_id)


@mock_kms_deprecated
def test__create_alias__raises_if_target_key_id_is_existing_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']
    alias = 'alias/my-alias'

    kms.create_alias(alias, key_id)

    with assert_raises(JSONResponseError) as err:
        kms.create_alias(alias, alias)

    ex = err.exception
    ex.body['__type'].should.equal('ValidationException')
    ex.body['message'].should.equal('Aliases must refer to keys. Not aliases')
    ex.error_code.should.equal('ValidationException')
    ex.message.should.equal('Aliases must refer to keys. Not aliases')
    ex.reason.should.equal('Bad Request')
    ex.status.should.equal(400)


@mock_kms_deprecated
def test__delete_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']
    alias = 'alias/my-alias'

    # added another alias here to make sure that the deletion of the alias can
    # be done when there are multiple existing aliases.
    another_create_resp = kms.create_key()
    another_key_id = create_resp['KeyMetadata']['KeyId']
    another_alias = 'alias/another-alias'

    kms.create_alias(alias, key_id)
    kms.create_alias(another_alias, another_key_id)

    resp = kms.delete_alias(alias)

    resp.should.be.none

    # we can create the alias again, since it has been deleted
    kms.create_alias(alias, key_id)


@mock_kms_deprecated
def test__delete_alias__raises_if_wrong_prefix():
    kms = boto.connect_kms()

    with assert_raises(JSONResponseError) as err:
        kms.delete_alias('wrongprefix/my-alias')

    ex = err.exception
    ex.body['__type'].should.equal('ValidationException')
    ex.body['message'].should.equal('Invalid identifier')
    ex.error_code.should.equal('ValidationException')
    ex.message.should.equal('Invalid identifier')
    ex.reason.should.equal('Bad Request')
    ex.status.should.equal(400)


@mock_kms_deprecated
def test__delete_alias__raises_if_alias_is_not_found():
    region = 'us-west-2'
    kms = boto.kms.connect_to_region(region)
    alias_name = 'alias/unexisting-alias'

    with assert_raises(NotFoundException) as err:
        kms.delete_alias(alias_name)

    ex = err.exception
    ex.body['__type'].should.equal('NotFoundException')
    ex.body['message'].should.match(
        r'Alias arn:aws:kms:{region}:\d{{12}}:{alias_name} is not found.'.format(**locals()))
    ex.box_usage.should.be.none
    ex.error_code.should.be.none
    ex.message.should.match(
        r'Alias arn:aws:kms:{region}:\d{{12}}:{alias_name} is not found.'.format(**locals()))
    ex.reason.should.equal('Bad Request')
    ex.request_id.should.be.none
    ex.status.should.equal(400)


@mock_kms_deprecated
def test__list_aliases():
    region = "eu-west-1"
    kms = boto.kms.connect_to_region(region)

    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']
    kms.create_alias('alias/my-alias1', key_id)
    kms.create_alias('alias/my-alias2', key_id)
    kms.create_alias('alias/my-alias3', key_id)

    resp = kms.list_aliases()

    resp['Truncated'].should.be.false

    aliases = resp['Aliases']

    def has_correct_arn(alias_obj):
        alias_name = alias_obj['AliasName']
        alias_arn = alias_obj['AliasArn']
        return re.match(r'arn:aws:kms:{region}:\d{{12}}:{alias_name}'.format(region=region, alias_name=alias_name),
                        alias_arn)

    len([alias for alias in aliases if
         has_correct_arn(alias) and 'alias/aws/ebs' == alias['AliasName']]).should.equal(1)
    len([alias for alias in aliases if
         has_correct_arn(alias) and 'alias/aws/rds' == alias['AliasName']]).should.equal(1)
    len([alias for alias in aliases if
         has_correct_arn(alias) and 'alias/aws/redshift' == alias['AliasName']]).should.equal(1)
    len([alias for alias in aliases if
         has_correct_arn(alias) and 'alias/aws/s3' == alias['AliasName']]).should.equal(1)

    len([alias for alias in aliases if
         has_correct_arn(alias) and 'alias/my-alias1' == alias['AliasName']]).should.equal(1)
    len([alias for alias in aliases if
         has_correct_arn(alias) and 'alias/my-alias2' == alias['AliasName']]).should.equal(1)

    len([alias for alias in aliases if 'TargetKeyId' in alias and key_id ==
         alias['TargetKeyId']]).should.equal(3)

    len(aliases).should.equal(7)


@mock_kms_deprecated
def test__assert_valid_key_id():
    from moto.kms.responses import _assert_valid_key_id
    import uuid

    _assert_valid_key_id.when.called_with(
        "not-a-key").should.throw(MotoNotFoundException)
    _assert_valid_key_id.when.called_with(
        str(uuid.uuid4())).should_not.throw(MotoNotFoundException)


@mock_kms_deprecated
def test__assert_default_policy():
    from moto.kms.responses import _assert_default_policy

    _assert_default_policy.when.called_with(
        "not-default").should.throw(MotoNotFoundException)
    _assert_default_policy.when.called_with(
        "default").should_not.throw(MotoNotFoundException)


@mock_kms
def test_kms_encrypt_boto3():
    client = boto3.client('kms', region_name='us-east-1')
    response = client.encrypt(KeyId='foo', Plaintext=b'bar')

    response = client.decrypt(CiphertextBlob=response['CiphertextBlob'])
    response['Plaintext'].should.equal(b'bar')


@mock_kms
def test_disable_key():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='disable-key')
    client.disable_key(
        KeyId=key['KeyMetadata']['KeyId']
    )

    result = client.describe_key(KeyId=key['KeyMetadata']['KeyId'])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == 'Disabled'


@mock_kms
def test_enable_key():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='enable-key')
    client.disable_key(
        KeyId=key['KeyMetadata']['KeyId']
    )
    client.enable_key(
        KeyId=key['KeyMetadata']['KeyId']
    )

    result = client.describe_key(KeyId=key['KeyMetadata']['KeyId'])
    assert result["KeyMetadata"]["Enabled"] == True
    assert result["KeyMetadata"]["KeyState"] == 'Enabled'


@mock_kms
def test_schedule_key_deletion():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='schedule-key-deletion')
    if os.environ.get('TEST_SERVER_MODE', 'false').lower() == 'false':
        with freeze_time("2015-01-01 12:00:00"):
            response = client.schedule_key_deletion(
                KeyId=key['KeyMetadata']['KeyId']
            )
            assert response['KeyId'] == key['KeyMetadata']['KeyId']
            assert response['DeletionDate'] == datetime(2015, 1, 31, 12, 0, tzinfo=tzutc())
    else:
        # Can't manipulate time in server mode
        response = client.schedule_key_deletion(
            KeyId=key['KeyMetadata']['KeyId']
        )
        assert response['KeyId'] == key['KeyMetadata']['KeyId']

    result = client.describe_key(KeyId=key['KeyMetadata']['KeyId'])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == 'PendingDeletion'
    assert 'DeletionDate' in result["KeyMetadata"]


@mock_kms
def test_schedule_key_deletion_custom():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='schedule-key-deletion')
    if os.environ.get('TEST_SERVER_MODE', 'false').lower() == 'false':
        with freeze_time("2015-01-01 12:00:00"):
            response = client.schedule_key_deletion(
                KeyId=key['KeyMetadata']['KeyId'],
                PendingWindowInDays=7
            )
            assert response['KeyId'] == key['KeyMetadata']['KeyId']
            assert response['DeletionDate'] == datetime(2015, 1, 8, 12, 0, tzinfo=tzutc())
    else:
        # Can't manipulate time in server mode
        response = client.schedule_key_deletion(
            KeyId=key['KeyMetadata']['KeyId'],
            PendingWindowInDays=7
        )
        assert response['KeyId'] == key['KeyMetadata']['KeyId']

    result = client.describe_key(KeyId=key['KeyMetadata']['KeyId'])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == 'PendingDeletion'
    assert 'DeletionDate' in result["KeyMetadata"]


@mock_kms
def test_cancel_key_deletion():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='cancel-key-deletion')
    client.schedule_key_deletion(
        KeyId=key['KeyMetadata']['KeyId']
    )
    response = client.cancel_key_deletion(
        KeyId=key['KeyMetadata']['KeyId']
    )
    assert response['KeyId'] == key['KeyMetadata']['KeyId']

    result = client.describe_key(KeyId=key['KeyMetadata']['KeyId'])
    assert result["KeyMetadata"]["Enabled"] == False
    assert result["KeyMetadata"]["KeyState"] == 'Disabled'
    assert 'DeletionDate' not in result["KeyMetadata"]


@mock_kms
def test_update_key_description():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='old_description')
    key_id =  key['KeyMetadata']['KeyId']

    result = client.update_key_description(KeyId=key_id, Description='new_description')
    assert 'ResponseMetadata' in result


@mock_kms
def test_tag_resource():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='cancel-key-deletion')
    response = client.schedule_key_deletion(
        KeyId=key['KeyMetadata']['KeyId']
    )

    keyid = response['KeyId']
    response = client.tag_resource(
        KeyId=keyid,
        Tags=[
            {
                'TagKey': 'string',
                'TagValue': 'string'
            },
        ]
    )

    # Shouldn't have any data, just header
    assert len(response.keys()) == 1


@mock_kms
def test_list_resource_tags():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='cancel-key-deletion')
    response = client.schedule_key_deletion(
        KeyId=key['KeyMetadata']['KeyId']
    )

    keyid = response['KeyId']
    response = client.tag_resource(
        KeyId=keyid,
        Tags=[
            {
                'TagKey': 'string',
                'TagValue': 'string'
            },
        ]
    )

    response = client.list_resource_tags(KeyId=keyid)
    assert response['Tags'][0]['TagKey'] == 'string'
    assert response['Tags'][0]['TagValue'] == 'string'


@mock_kms
def test_generate_data_key_sizes():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='generate-data-key-size')

    resp1 = client.generate_data_key(
        KeyId=key['KeyMetadata']['KeyId'],
        KeySpec='AES_256'
    )
    resp2 = client.generate_data_key(
        KeyId=key['KeyMetadata']['KeyId'],
        KeySpec='AES_128'
    )
    resp3 = client.generate_data_key(
        KeyId=key['KeyMetadata']['KeyId'],
        NumberOfBytes=64
    )

    assert len(resp1['Plaintext']) == 32
    assert len(resp2['Plaintext']) == 16
    assert len(resp3['Plaintext']) == 64


@mock_kms
def test_generate_data_key_decrypt():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='generate-data-key-decrypt')

    resp1 = client.generate_data_key(
        KeyId=key['KeyMetadata']['KeyId'],
        KeySpec='AES_256'
    )
    resp2 = client.decrypt(
        CiphertextBlob=resp1['CiphertextBlob']
    )

    assert resp1['Plaintext'] == resp2['Plaintext']


@mock_kms
def test_generate_data_key_invalid_size_params():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='generate-data-key-size')

    with assert_raises(botocore.exceptions.ClientError) as err:
        client.generate_data_key(
            KeyId=key['KeyMetadata']['KeyId'],
            KeySpec='AES_257'
        )

    with assert_raises(botocore.exceptions.ClientError) as err:
        client.generate_data_key(
            KeyId=key['KeyMetadata']['KeyId'],
            KeySpec='AES_128',
            NumberOfBytes=16
        )

    with assert_raises(botocore.exceptions.ClientError) as err:
        client.generate_data_key(
            KeyId=key['KeyMetadata']['KeyId'],
            NumberOfBytes=2048
        )

    with assert_raises(botocore.exceptions.ClientError) as err:
        client.generate_data_key(
            KeyId=key['KeyMetadata']['KeyId']
        )


@mock_kms
def test_generate_data_key_invalid_key():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='generate-data-key-size')

    with assert_raises(client.exceptions.NotFoundException):
        client.generate_data_key(
            KeyId='alias/randomnonexistantkey',
            KeySpec='AES_256'
        )

    with assert_raises(client.exceptions.NotFoundException):
        client.generate_data_key(
            KeyId=key['KeyMetadata']['KeyId'] + '4',
            KeySpec='AES_256'
        )


@mock_kms
def test_generate_data_key_without_plaintext_decrypt():
    client = boto3.client('kms', region_name='us-east-1')
    key = client.create_key(Description='generate-data-key-decrypt')

    resp1 = client.generate_data_key_without_plaintext(
        KeyId=key['KeyMetadata']['KeyId'],
        KeySpec='AES_256'
    )

    assert 'Plaintext' not in resp1


@mock_kms
def test_enable_key_rotation_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.enable_key_rotation(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_disable_key_rotation_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.disable_key_rotation(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_enable_key_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.enable_key(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_disable_key_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.disable_key(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_cancel_key_deletion_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.cancel_key_deletion(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_schedule_key_deletion_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.schedule_key_deletion(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_get_key_rotation_status_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.get_key_rotation_status(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_get_key_policy_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.get_key_policy(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02',
            PolicyName='default'
        )


@mock_kms
def test_list_key_policies_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.list_key_policies(
            KeyId='12366f9b-1230-123d-123e-123e6ae60c02'
        )


@mock_kms
def test_put_key_policy_key_not_found():
    client = boto3.client('kms', region_name='us-east-1')

    with assert_raises(client.exceptions.NotFoundException):
        client.put_key_policy(
            KeyId='00000000-0000-0000-0000-000000000000',
            PolicyName='default',
            Policy='new policy'
        )
