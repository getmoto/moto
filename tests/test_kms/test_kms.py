from __future__ import unicode_literals
import re

import boto.kms
from boto.exception import JSONResponseError
from boto.kms.exceptions import AlreadyExistsException, NotFoundException
import sure  # noqa
from moto import mock_kms
from nose.tools import assert_raises

@mock_kms
def test_create_key():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')

    key['KeyMetadata']['Description'].should.equal("my key")
    key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")
    key['KeyMetadata']['Enabled'].should.equal(True)


@mock_kms
def test_describe_key():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    key = conn.describe_key(key_id)
    key['KeyMetadata']['Description'].should.equal("my key")
    key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")


@mock_kms
def test_describe_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.describe_key.when.called_with("not-a-key").should.throw(JSONResponseError)


@mock_kms
def test_list_keys():
    conn = boto.kms.connect_to_region("us-west-2")

    conn.create_key(policy="my policy", description="my key1", key_usage='ENCRYPT_DECRYPT')
    conn.create_key(policy="my policy", description="my key2", key_usage='ENCRYPT_DECRYPT')

    keys = conn.list_keys()
    keys['Keys'].should.have.length_of(2)


@mock_kms
def test_enable_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.enable_key_rotation(key_id)

    conn.get_key_rotation_status(key_id)['KeyRotationEnabled'].should.equal(True)


@mock_kms
def test_enable_key_rotation_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.enable_key_rotation.when.called_with("not-a-key").should.throw(JSONResponseError)


@mock_kms
def test_disable_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.enable_key_rotation(key_id)
    conn.get_key_rotation_status(key_id)['KeyRotationEnabled'].should.equal(True)

    conn.disable_key_rotation(key_id)
    conn.get_key_rotation_status(key_id)['KeyRotationEnabled'].should.equal(False)


@mock_kms
def test_disable_key_rotation_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.disable_key_rotation.when.called_with("not-a-key").should.throw(JSONResponseError)


@mock_kms
def test_get_key_rotation_status_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.get_key_rotation_status.when.called_with("not-a-key").should.throw(JSONResponseError)


@mock_kms
def test_get_key_rotation_status():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.get_key_rotation_status(key_id)['KeyRotationEnabled'].should.equal(False)


@mock_kms
def test_create_key_defaults_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.get_key_rotation_status(key_id)['KeyRotationEnabled'].should.equal(False)


@mock_kms
def test_get_key_policy():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy', description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    policy = conn.get_key_policy(key_id, 'default')
    policy['Policy'].should.equal('my policy')


@mock_kms
def test_put_key_policy():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy', description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    conn.put_key_policy(key_id, 'default', 'new policy')
    policy = conn.get_key_policy(key_id, 'default')
    policy['Policy'].should.equal('new policy')


@mock_kms
def test_list_key_policies():
    conn = boto.kms.connect_to_region('us-west-2')

    key = conn.create_key(policy='my policy', description='my key1', key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    policies = conn.list_key_policies(key_id)
    policies['PolicyNames'].should.equal(['default'])


@mock_kms
def test__create_alias__returns_none_if_correct():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    resp = kms.create_alias('alias/my-alias', key_id)

    resp.should.be.none


@mock_kms
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


@mock_kms
def test__create_alias__can_create_multiple_aliases_for_same_key_id():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    kms.create_alias('alias/my-alias3', key_id).should.be.none
    kms.create_alias('alias/my-alias4', key_id).should.be.none
    kms.create_alias('alias/my-alias5', key_id).should.be.none


@mock_kms
def test__create_alias__raises_if_wrong_prefix():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']

    with assert_raises(JSONResponseError) as err:
        kms.create_alias('wrongprefix/my-alias', key_id)

    ex = err.exception
    ex.error_message.should.equal('Invalid identifier')
    ex.error_code.should.equal('ValidationException')
    ex.body.should.equal({'message': 'Invalid identifier', '__type': 'ValidationException'})
    ex.reason.should.equal('Bad Request')
    ex.status.should.equal(400)


@mock_kms
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


@mock_kms
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
        ex.body['message'].should.equal("1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$".format(**locals()))
        ex.error_code.should.equal('ValidationException')
        ex.message.should.equal("1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$".format(**locals()))
        ex.reason.should.equal('Bad Request')
        ex.status.should.equal(400)


@mock_kms
def test__create_alias__raises_if_alias_has_colon_character():
    # For some reason, colons are not accepted for an alias, even though they are accepted by regex ^[a-zA-Z0-9:/_-]+$
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
        ex.body['message'].should.equal("{alias_name} contains invalid characters for an alias".format(**locals()))
        ex.error_code.should.equal('ValidationException')
        ex.message.should.equal("{alias_name} contains invalid characters for an alias".format(**locals()))
        ex.reason.should.equal('Bad Request')
        ex.status.should.equal(400)


@mock_kms
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


@mock_kms
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


@mock_kms
def test__delete_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp['KeyMetadata']['KeyId']
    alias = 'alias/my-alias'

    kms.create_alias(alias, key_id)

    resp = kms.delete_alias(alias)

    resp.should.be.none

    # we can create the alias again, since it has been deleted
    kms.create_alias(alias, key_id)


@mock_kms
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


@mock_kms
def test__delete_alias__raises_if_alias_is_not_found():
    region = 'us-west-2'
    kms = boto.kms.connect_to_region(region)
    alias_name = 'alias/unexisting-alias'

    with assert_raises(NotFoundException) as err:
        kms.delete_alias(alias_name)

    ex = err.exception
    ex.body['__type'].should.equal('NotFoundException')
    ex.body['message'].should.match(r'Alias arn:aws:kms:{region}:\d{{12}}:{alias_name} is not found.'.format(**locals()))
    ex.box_usage.should.be.none
    ex.error_code.should.be.none
    ex.message.should.match(r'Alias arn:aws:kms:{region}:\d{{12}}:{alias_name} is not found.'.format(**locals()))
    ex.reason.should.equal('Bad Request')
    ex.request_id.should.be.none
    ex.status.should.equal(400)


@mock_kms
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

    len([alias for alias in aliases if 'TargetKeyId' in alias and key_id == alias['TargetKeyId']]).should.equal(3)

    len(aliases).should.equal(7)


@mock_kms
def test__assert_valid_key_id():
    from moto.kms.responses import _assert_valid_key_id
    import uuid

    _assert_valid_key_id.when.called_with("not-a-key").should.throw(JSONResponseError)
    _assert_valid_key_id.when.called_with(str(uuid.uuid4())).should_not.throw(JSONResponseError)


@mock_kms
def test__assert_default_policy():
    from moto.kms.responses import _assert_default_policy

    _assert_default_policy.when.called_with("not-default").should.throw(JSONResponseError)
    _assert_default_policy.when.called_with("default").should_not.throw(JSONResponseError)
