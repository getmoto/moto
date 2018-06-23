from __future__ import unicode_literals

import boto3
import sure  # noqa
import json
from moto import mock_iot


@mock_iot
def test_things():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-thing'
    type_name = 'my-type-name'

    # thing type
    thing_type = client.create_thing_type(thingTypeName=type_name)
    thing_type.should.have.key('thingTypeName').which.should.equal(type_name)
    thing_type.should.have.key('thingTypeArn')

    res = client.list_thing_types()
    res.should.have.key('thingTypes').which.should.have.length_of(1)
    for thing_type in res['thingTypes']:
        thing_type.should.have.key('thingTypeName').which.should_not.be.none

    thing_type = client.describe_thing_type(thingTypeName=type_name)
    thing_type.should.have.key('thingTypeName').which.should.equal(type_name)
    thing_type.should.have.key('thingTypeProperties')
    thing_type.should.have.key('thingTypeMetadata')

    # thing
    thing = client.create_thing(thingName=name, thingTypeName=type_name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should.have.key('thingName').which.should_not.be.none
        thing.should.have.key('thingArn').which.should_not.be.none

    thing = client.update_thing(thingName=name, attributePayload={'attributes': {'k1': 'v1'}})
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should.have.key('thingName').which.should_not.be.none
        thing.should.have.key('thingArn').which.should_not.be.none
    res['things'][0]['attributes'].should.have.key('k1').which.should.equal('v1')

    thing = client.describe_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('defaultClientId')
    thing.should.have.key('thingTypeName')
    thing.should.have.key('attributes')
    thing.should.have.key('version')

    # delete thing
    client.delete_thing(thingName=name)
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(0)

    # delete thing type
    client.delete_thing_type(thingTypeName=type_name)
    res = client.list_thing_types()
    res.should.have.key('thingTypes').which.should.have.length_of(0)


@mock_iot
def test_certs():
    client = boto3.client('iot', region_name='ap-northeast-1')
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert.should.have.key('certificateArn').which.should_not.be.none
    cert.should.have.key('certificateId').which.should_not.be.none
    cert.should.have.key('certificatePem').which.should_not.be.none
    cert.should.have.key('keyPair')
    cert['keyPair'].should.have.key('PublicKey').which.should_not.be.none
    cert['keyPair'].should.have.key('PrivateKey').which.should_not.be.none
    cert_id = cert['certificateId']

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key('certificateDescription')
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('certificateArn').which.should_not.be.none
    cert_desc.should.have.key('certificateId').which.should_not.be.none
    cert_desc.should.have.key('certificatePem').which.should_not.be.none
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')

    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(1)
    for cert in res['certificates']:
        cert.should.have.key('certificateArn').which.should_not.be.none
        cert.should.have.key('certificateId').which.should_not.be.none
        cert.should.have.key('status').which.should_not.be.none
        cert.should.have.key('creationDate').which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus='REVOKED')
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(0)


@mock_iot
def test_certs_create_inactive():
    client = boto3.client('iot', region_name='ap-northeast-1')
    cert = client.create_keys_and_certificate(setAsActive=False)
    cert_id = cert['certificateId']

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key('certificateDescription')
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('status').which.should.equal('INACTIVE')

    client.update_certificate(certificateId=cert_id, newStatus='ACTIVE')
    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key('certificateDescription')
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')


@mock_iot
def test_policy():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-policy'
    doc = '{}'
    policy = client.create_policy(policyName=name, policyDocument=doc)
    policy.should.have.key('policyName').which.should.equal(name)
    policy.should.have.key('policyArn').which.should_not.be.none
    policy.should.have.key('policyDocument').which.should.equal(doc)
    policy.should.have.key('policyVersionId').which.should.equal('1')

    policy = client.get_policy(policyName=name)
    policy.should.have.key('policyName').which.should.equal(name)
    policy.should.have.key('policyArn').which.should_not.be.none
    policy.should.have.key('policyDocument').which.should.equal(doc)
    policy.should.have.key('defaultVersionId').which.should.equal('1')

    res = client.list_policies()
    res.should.have.key('policies').which.should.have.length_of(1)
    for policy in res['policies']:
        policy.should.have.key('policyName').which.should_not.be.none
        policy.should.have.key('policyArn').which.should_not.be.none

    client.delete_policy(policyName=name)
    res = client.list_policies()
    res.should.have.key('policies').which.should.have.length_of(0)


@mock_iot
def test_principal_policy():
    client = boto3.client('iot', region_name='ap-northeast-1')
    policy_name = 'my-policy'
    doc = '{}'
    policy = client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert['certificateArn']

    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(1)
    for policy in res['policies']:
        policy.should.have.key('policyName').which.should_not.be.none
        policy.should.have.key('policyArn').which.should_not.be.none

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key('principals').which.should.have.length_of(1)
    for principal in res['principals']:
        principal.should_not.be.none

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key('principals').which.should.have.length_of(0)


@mock_iot
def test_principal_thing():
    client = boto3.client('iot', region_name='ap-northeast-1')
    thing_name = 'my-thing'
    thing = client.create_thing(thingName=thing_name)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert['certificateArn']

    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should_not.be.none
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key('principals').which.should.have.length_of(1)
    for principal in res['principals']:
        principal.should_not.be.none

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key('things').which.should.have.length_of(0)
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key('principals').which.should.have.length_of(0)


@mock_iot
def test_thing_groups():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-thing'
    group_name = 'my-group-name'

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupArn')

    res = client.list_thing_groups()
    res.should.have.key('thingGroups').which.should.have.length_of(1)
    for thing_group in res['thingGroups']:
        thing_group.should.have.key('groupName').which.should_not.be.none
        thing_group.should.have.key('groupArn').which.should_not.be.none

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupProperties')
    thing_group.should.have.key('thingGroupMetadata')
    thing_group.should.have.key('version')

    # delete thing group
    client.delete_thing_group(thingGroupName=group_name)
    res = client.list_thing_groups()
    res.should.have.key('thingGroups').which.should.have.length_of(0)

    # props create test
    props = {
        'thingGroupDescription': 'my first thing group',
        'attributePayload': {
            'attributes': {
                'key1': 'val01',
                'Key02': 'VAL2'
            }
        }
    }
    thing_group = client.create_thing_group(thingGroupName=group_name, thingGroupProperties=props)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupArn')

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupProperties') \
        .which.should.have.key('attributePayload') \
        .which.should.have.key('attributes')
    res_props = thing_group['thingGroupProperties']['attributePayload']['attributes']
    res_props.should.have.key('key1').which.should.equal('val01')
    res_props.should.have.key('Key02').which.should.equal('VAL2')

    # props update test with merge
    new_props = {
        'attributePayload': {
            'attributes': {
                'k3': 'v3'
            },
            'merge': True
        }
    }
    client.update_thing_group(
        thingGroupName=group_name,
        thingGroupProperties=new_props
    )
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupProperties') \
        .which.should.have.key('attributePayload') \
        .which.should.have.key('attributes')
    res_props = thing_group['thingGroupProperties']['attributePayload']['attributes']
    res_props.should.have.key('key1').which.should.equal('val01')
    res_props.should.have.key('Key02').which.should.equal('VAL2')

    res_props.should.have.key('k3').which.should.equal('v3')

    # props update test
    new_props = {
        'attributePayload': {
            'attributes': {
                'k4': 'v4'
            }
        }
    }
    client.update_thing_group(
        thingGroupName=group_name,
        thingGroupProperties=new_props
    )
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupProperties') \
        .which.should.have.key('attributePayload') \
        .which.should.have.key('attributes')
    res_props = thing_group['thingGroupProperties']['attributePayload']['attributes']
    res_props.should.have.key('k4').which.should.equal('v4')
    res_props.should_not.have.key('key1')


@mock_iot
def test_thing_group_relations():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-thing'
    group_name = 'my-group-name'

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupArn')

    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    # add in 4 way
    client.add_thing_to_thing_group(
        thingGroupName=group_name,
        thingName=name
    )
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingArn=thing['thingArn']
    )
    client.add_thing_to_thing_group(
        thingGroupName=group_name,
        thingArn=thing['thingArn']
    )
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingName=name
    )

    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(1)

    thing_groups = client.list_thing_groups_for_thing(
        thingName=name
    )
    thing_groups.should.have.key('thingGroups')
    thing_groups['thingGroups'].should.have.length_of(1)

    # remove in 4 way
    client.remove_thing_from_thing_group(
        thingGroupName=group_name,
        thingName=name
    )
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingArn=thing['thingArn']
    )
    client.remove_thing_from_thing_group(
        thingGroupName=group_name,
        thingArn=thing['thingArn']
    )
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingName=name
    )
    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(0)

    # update thing group for thing
    client.update_thing_groups_for_thing(
        thingName=name,
        thingGroupsToAdd=[
            group_name
        ]
    )
    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(1)

    client.update_thing_groups_for_thing(
        thingName=name,
        thingGroupsToRemove=[
            group_name
        ]
    )
    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(0)


@mock_iot
def test_create_job():
    client = boto3.client('iot', region_name='eu-west-1')
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    # job document
    job_document = {
        "field": "value"
    }

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            'roleArn': 'arn:aws:iam::1:role/service-role/iot_job_role',
            'expiresInSec': 123
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={
            'maximumPerMinute': 10
        }
    )

    job.should.have.key('jobId').which.should.equal(job_id)
    job.should.have.key('jobArn')
    job.should.have.key('description')

@mock_iot
def test_describe_job():
    client = boto3.client('iot', region_name='eu-west-1')
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            'roleArn': 'arn:aws:iam::1:role/service-role/iot_job_role',
            'expiresInSec': 123
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={
            'maximumPerMinute': 10
        }
    )

    job.should.have.key('jobId').which.should.equal(job_id)
    job.should.have.key('jobArn')

    job = client.describe_job(jobId=job_id)
    job.should.have.key('documentSource')
    job.should.have.key('job')
    job.should.have.key('job').which.should.have.key("jobArn")
    job.should.have.key('job').which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key('job').which.should.have.key("targets")
    job.should.have.key('job').which.should.have.key("jobProcessDetails")
    job.should.have.key('job').which.should.have.key("lastUpdatedAt")
    job.should.have.key('job').which.should.have.key("createdAt")
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key('job').which.should.have.key("targetSelection").which.should.equal("CONTINUOUS")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "roleArn").which.should.equal('arn:aws:iam::1:role/service-role/iot_job_role')
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "expiresInSec").which.should.equal(123)
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig").which.should.have.key(
        "maximumPerMinute").which.should.equal(10)


@mock_iot
def test_describe_job_1():
    client = boto3.client('iot', region_name='eu-west-1')
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    # job document
    job_document = {
        "field": "value"
    }

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        presignedUrlConfig={
            'roleArn': 'arn:aws:iam::1:role/service-role/iot_job_role',
            'expiresInSec': 123
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={
            'maximumPerMinute': 10
        }
    )

    job.should.have.key('jobId').which.should.equal(job_id)
    job.should.have.key('jobArn')

    job = client.describe_job(jobId=job_id)
    job.should.have.key('job')
    job.should.have.key('job').which.should.have.key("jobArn")
    job.should.have.key('job').which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key('job').which.should.have.key("targets")
    job.should.have.key('job').which.should.have.key("jobProcessDetails")
    job.should.have.key('job').which.should.have.key("lastUpdatedAt")
    job.should.have.key('job').which.should.have.key("createdAt")
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key('job').which.should.have.key("targetSelection").which.should.equal("CONTINUOUS")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "roleArn").which.should.equal('arn:aws:iam::1:role/service-role/iot_job_role')
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "expiresInSec").which.should.equal(123)
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig").which.should.have.key(
        "maximumPerMinute").which.should.equal(10)
