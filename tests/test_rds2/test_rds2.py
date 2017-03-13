from __future__ import unicode_literals

from botocore.exceptions import ClientError, ParamValidationError
import boto3
import sure  # noqa
from moto import mock_ec2, mock_kms, mock_rds2
from tests.helpers import disable_on_py3


@disable_on_py3()
@mock_rds2
def test_create_database():
    conn = boto3.client('rds', region_name='us-west-2')
    database = conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                                       AllocatedStorage=10,
                                       Engine='postgres',
                                       DBInstanceClass='db.m1.small',
                                       MasterUsername='root',
                                       MasterUserPassword='hunter2',
                                       Port=1234,
                                       DBSecurityGroups=["my_sg"])
    database['DBInstance']['DBInstanceStatus'].should.equal('available')
    database['DBInstance']['DBInstanceIdentifier'].should.equal("db-master-1")
    database['DBInstance']['AllocatedStorage'].should.equal(10)
    database['DBInstance']['DBInstanceClass'].should.equal("db.m1.small")
    database['DBInstance']['MasterUsername'].should.equal("root")
    database['DBInstance']['DBSecurityGroups'][0][
        'DBSecurityGroupName'].should.equal('my_sg')
    database['DBInstance']['DBInstanceArn'].should.equal(
        'arn:aws:rds:us-west-2:1234567890:db:db-master-1')


@disable_on_py3()
@mock_rds2
def test_get_databases():
    conn = boto3.client('rds', region_name='us-west-2')

    instances = conn.describe_db_instances()
    list(instances['DBInstances']).should.have.length_of(0)

    conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=['my_sg'])
    conn.create_db_instance(DBInstanceIdentifier='db-master-2',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=['my_sg'])
    instances = conn.describe_db_instances()
    list(instances['DBInstances']).should.have.length_of(2)

    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    list(instances['DBInstances']).should.have.length_of(1)
    instances['DBInstances'][0][
        'DBInstanceIdentifier'].should.equal("db-master-1")
    instances['DBInstances'][0]['DBInstanceArn'].should.equal(
        'arn:aws:rds:us-west-2:1234567890:db:db-master-1')


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_database():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.describe_db_instances.when.called_with(
        DBInstanceIdentifier="not-a-db").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_modify_db_instance():
    conn = boto3.client('rds', region_name='us-west-2')
    database = conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                                       AllocatedStorage=10,
                                       DBInstanceClass='postgres',
                                       Engine='db.m1.small',
                                       MasterUsername='root',
                                       MasterUserPassword='hunter2',
                                       Port=1234,
                                       DBSecurityGroups=['my_sg'])
    instances = conn.describe_db_instances(DBInstanceIdentifier='db-master-1')
    instances['DBInstances'][0]['AllocatedStorage'].should.equal(10)
    conn.modify_db_instance(DBInstanceIdentifier='db-master-1',
                            AllocatedStorage=20,
                            ApplyImmediately=True)
    instances = conn.describe_db_instances(DBInstanceIdentifier='db-master-1')
    instances['DBInstances'][0]['AllocatedStorage'].should.equal(20)


@disable_on_py3()
@mock_rds2
def test_modify_non_existant_database():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.modify_db_instance.when.called_with(DBInstanceIdentifier='not-a-db',
                                             AllocatedStorage=20,
                                             ApplyImmediately=True).should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_reboot_db_instance():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=['my_sg'])
    database = conn.reboot_db_instance(DBInstanceIdentifier='db-master-1')
    database['DBInstance']['DBInstanceIdentifier'].should.equal("db-master-1")


@disable_on_py3()
@mock_rds2
def test_reboot_non_existant_database():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.reboot_db_instance.when.called_with(
        DBInstanceIdentifier="not-a-db").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_delete_database():
    conn = boto3.client('rds', region_name='us-west-2')
    instances = conn.describe_db_instances()
    list(instances['DBInstances']).should.have.length_of(0)
    conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=['my_sg'])
    instances = conn.describe_db_instances()
    list(instances['DBInstances']).should.have.length_of(1)

    conn.delete_db_instance(DBInstanceIdentifier="db-master-1")
    instances = conn.describe_db_instances()
    list(instances['DBInstances']).should.have.length_of(0)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_database():
    conn = boto3.client('rds2', region_name="us-west-2")
    conn.delete_db_instance.when.called_with(
        DBInstanceIdentifier="not-a-db").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_create_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    option_group = conn.create_option_group(OptionGroupName='test',
                                            EngineName='mysql',
                                            MajorEngineVersion='5.6',
                                            OptionGroupDescription='test option group')
    option_group['OptionGroup']['OptionGroupName'].should.equal('test')
    option_group['OptionGroup']['EngineName'].should.equal('mysql')
    option_group['OptionGroup'][
        'OptionGroupDescription'].should.equal('test option group')
    option_group['OptionGroup']['MajorEngineVersion'].should.equal('5.6')


@disable_on_py3()
@mock_rds2
def test_create_option_group_bad_engine_name():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group.when.called_with(OptionGroupName='test',
                                              EngineName='invalid_engine',
                                              MajorEngineVersion='5.6',
                                              OptionGroupDescription='test invalid engine').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_bad_engine_major_version():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group.when.called_with(OptionGroupName='test',
                                              EngineName='mysql',
                                              MajorEngineVersion='6.6.6',
                                              OptionGroupDescription='test invalid engine version').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_empty_description():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group.when.called_with(OptionGroupName='test',
                                              EngineName='mysql',
                                              MajorEngineVersion='5.6',
                                              OptionGroupDescription='').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_duplicate():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test',
                             EngineName='mysql',
                             MajorEngineVersion='5.6',
                             OptionGroupDescription='test option group')
    conn.create_option_group.when.called_with(OptionGroupName='test',
                                              EngineName='mysql',
                                              MajorEngineVersion='5.6',
                                              OptionGroupDescription='test option group').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_describe_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test',
                             EngineName='mysql',
                             MajorEngineVersion='5.6',
                             OptionGroupDescription='test option group')
    option_groups = conn.describe_option_groups(OptionGroupName='test')
    option_groups['OptionGroupsList'][0][
        'OptionGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.describe_option_groups.when.called_with(
        OptionGroupName="not-a-option-group").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_delete_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test',
                             EngineName='mysql',
                             MajorEngineVersion='5.6',
                             OptionGroupDescription='test option group')
    option_groups = conn.describe_option_groups(OptionGroupName='test')
    option_groups['OptionGroupsList'][0][
        'OptionGroupName'].should.equal('test')
    conn.delete_option_group(OptionGroupName='test')
    conn.describe_option_groups.when.called_with(
        OptionGroupName='test').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.delete_option_group.when.called_with(
        OptionGroupName='non-existant').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_describe_option_group_options():
    conn = boto3.client('rds', region_name='us-west-2')
    option_group_options = conn.describe_option_group_options(
        EngineName='sqlserver-ee')
    len(option_group_options['OptionGroupOptions']).should.equal(4)
    option_group_options = conn.describe_option_group_options(
        EngineName='sqlserver-ee', MajorEngineVersion='11.00')
    len(option_group_options['OptionGroupOptions']).should.equal(2)
    option_group_options = conn.describe_option_group_options(
        EngineName='mysql', MajorEngineVersion='5.6')
    len(option_group_options['OptionGroupOptions']).should.equal(1)
    conn.describe_option_group_options.when.called_with(
        EngineName='non-existent').should.throw(ClientError)
    conn.describe_option_group_options.when.called_with(
        EngineName='mysql', MajorEngineVersion='non-existent').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_modify_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test', EngineName='mysql',
                             MajorEngineVersion='5.6', OptionGroupDescription='test option group')
    # TODO: create option and validate before deleting.
    # if Someone can tell me how the hell to use this function
    # to add options to an option_group, I can finish coding this.
    result = conn.modify_option_group(OptionGroupName='test', OptionsToInclude=[
    ], OptionsToRemove=['MEMCACHED'], ApplyImmediately=True)
    result['OptionGroup']['EngineName'].should.equal('mysql')
    result['OptionGroup']['Options'].should.equal([])
    result['OptionGroup']['OptionGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_modify_option_group_no_options():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test', EngineName='mysql',
                             MajorEngineVersion='5.6', OptionGroupDescription='test option group')
    conn.modify_option_group.when.called_with(
        OptionGroupName='test').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_modify_non_existant_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.modify_option_group.when.called_with(OptionGroupName='non-existant', OptionsToInclude=[(
        'OptionName', 'Port', 'DBSecurityGroupMemberships', 'VpcSecurityGroupMemberships', 'OptionSettings')]).should.throw(ParamValidationError)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_database():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.delete_db_instance.when.called_with(
        DBInstanceIdentifier="not-a-db").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_list_tags_invalid_arn():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.list_tags_for_resource.when.called_with(
        ResourceName='arn:aws:rds:bad-arn').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_list_tags_db():
    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:db:foo')
    result['TagList'].should.equal([])
    test_instance = conn.create_db_instance(
        DBInstanceIdentifier='db-with-tags',
        AllocatedStorage=10,
        DBInstanceClass='postgres',
        Engine='db.m1.small',
        MasterUsername='root',
        MasterUserPassword='hunter2',
        Port=1234,
        DBSecurityGroups=['my_sg'],
        Tags=[
            {
                'Key': 'foo',
                'Value': 'bar',
            },
            {
                'Key': 'foo1',
                'Value': 'bar1',
            },
        ])
    result = conn.list_tags_for_resource(
        ResourceName=test_instance['DBInstance']['DBInstanceArn'])
    result['TagList'].should.equal([{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])


@disable_on_py3()
@mock_rds2
def test_add_tags_db():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_instance(DBInstanceIdentifier='db-without-tags',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=['my_sg'],
                            Tags=[
                                {
                                    'Key': 'foo',
                                    'Value': 'bar',
                                },
                                {
                                    'Key': 'foo1',
                                    'Value': 'bar1',
                                },
                            ])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:db:db-without-tags')
    list(result['TagList']).should.have.length_of(2)
    conn.add_tags_to_resource(ResourceName='arn:aws:rds:us-west-2:1234567890:db:db-without-tags',
                              Tags=[
                                  {
                                      'Key': 'foo',
                                      'Value': 'fish',
                                  },
                                  {
                                      'Key': 'foo2',
                                      'Value': 'bar2',
                                  },
                              ])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:db:db-without-tags')
    list(result['TagList']).should.have.length_of(3)


@disable_on_py3()
@mock_rds2
def test_remove_tags_db():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_instance(DBInstanceIdentifier='db-with-tags',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSecurityGroups=['my_sg'],
                            Tags=[
                                {
                                    'Key': 'foo',
                                    'Value': 'bar',
                                },
                                {
                                    'Key': 'foo1',
                                    'Value': 'bar1',
                                },
                            ])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:db:db-with-tags')
    list(result['TagList']).should.have.length_of(2)
    conn.remove_tags_from_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:db:db-with-tags', TagKeys=['foo'])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:db:db-with-tags')
    len(result['TagList']).should.equal(1)


@disable_on_py3()
@mock_rds2
def test_add_tags_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test',
                             EngineName='mysql',
                             MajorEngineVersion='5.6',
                             OptionGroupDescription='test option group')
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['TagList']).should.have.length_of(0)
    conn.add_tags_to_resource(ResourceName='arn:aws:rds:us-west-2:1234567890:og:test',
                              Tags=[
                                  {
                                      'Key': 'foo',
                                      'Value': 'fish',
                                  },
                                  {
                                      'Key': 'foo2',
                                      'Value': 'bar2',
                                  }])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['TagList']).should.have.length_of(2)


@disable_on_py3()
@mock_rds2
def test_remove_tags_option_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_option_group(OptionGroupName='test',
                             EngineName='mysql',
                             MajorEngineVersion='5.6',
                             OptionGroupDescription='test option group')
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:og:test')
    conn.add_tags_to_resource(ResourceName='arn:aws:rds:us-west-2:1234567890:og:test',
                              Tags=[
                                  {
                                      'Key': 'foo',
                                      'Value': 'fish',
                                  },
                                  {
                                      'Key': 'foo2',
                                      'Value': 'bar2',
                                  }])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['TagList']).should.have.length_of(2)
    conn.remove_tags_from_resource(ResourceName='arn:aws:rds:us-west-2:1234567890:og:test',
                                   TagKeys=['foo'])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['TagList']).should.have.length_of(1)


@disable_on_py3()
@mock_rds2
def test_create_database_security_group():
    conn = boto3.client('rds', region_name='us-west-2')

    result = conn.create_db_security_group(
        DBSecurityGroupName='db_sg', DBSecurityGroupDescription='DB Security Group')
    result['DBSecurityGroup']['DBSecurityGroupName'].should.equal("db_sg")
    result['DBSecurityGroup'][
        'DBSecurityGroupDescription'].should.equal("DB Security Group")
    result['DBSecurityGroup']['IPRanges'].should.equal([])


@disable_on_py3()
@mock_rds2
def test_get_security_groups():
    conn = boto3.client('rds', region_name='us-west-2')

    result = conn.describe_db_security_groups()
    result['DBSecurityGroups'].should.have.length_of(0)

    conn.create_db_security_group(
        DBSecurityGroupName='db_sg1', DBSecurityGroupDescription='DB Security Group')
    conn.create_db_security_group(
        DBSecurityGroupName='db_sg2', DBSecurityGroupDescription='DB Security Group')

    result = conn.describe_db_security_groups()
    result['DBSecurityGroups'].should.have.length_of(2)

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg1")
    result['DBSecurityGroups'].should.have.length_of(1)
    result['DBSecurityGroups'][0]['DBSecurityGroupName'].should.equal("db_sg1")


@disable_on_py3()
@mock_rds2
def test_get_non_existant_security_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.describe_db_security_groups.when.called_with(
        DBSecurityGroupName="not-a-sg").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_delete_database_security_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_security_group(
        DBSecurityGroupName='db_sg', DBSecurityGroupDescription='DB Security Group')

    result = conn.describe_db_security_groups()
    result['DBSecurityGroups'].should.have.length_of(1)

    conn.delete_db_security_group(DBSecurityGroupName="db_sg")
    result = conn.describe_db_security_groups()
    result['DBSecurityGroups'].should.have.length_of(0)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_security_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.delete_db_security_group.when.called_with(
        DBSecurityGroupName="not-a-db").should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_security_group_authorize():
    conn = boto3.client('rds', region_name='us-west-2')
    security_group = conn.create_db_security_group(DBSecurityGroupName='db_sg',
                                                   DBSecurityGroupDescription='DB Security Group')
    security_group['DBSecurityGroup']['IPRanges'].should.equal([])

    conn.authorize_db_security_group_ingress(DBSecurityGroupName='db_sg',
                                             CIDRIP='10.3.2.45/32')

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    result['DBSecurityGroups'][0]['IPRanges'].should.have.length_of(1)
    result['DBSecurityGroups'][0]['IPRanges'].should.equal(
        [{'Status': 'authorized', 'CIDRIP': '10.3.2.45/32'}])

    conn.authorize_db_security_group_ingress(DBSecurityGroupName='db_sg',
                                             CIDRIP='10.3.2.46/32')
    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    result['DBSecurityGroups'][0]['IPRanges'].should.have.length_of(2)
    result['DBSecurityGroups'][0]['IPRanges'].should.equal([
        {'Status': 'authorized', 'CIDRIP': '10.3.2.45/32'},
        {'Status': 'authorized', 'CIDRIP': '10.3.2.46/32'},
    ])


@disable_on_py3()
@mock_rds2
def test_add_security_group_to_database():
    conn = boto3.client('rds', region_name='us-west-2')

    conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                            AllocatedStorage=10,
                            DBInstanceClass='postgres',
                            Engine='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234)

    result = conn.describe_db_instances()
    result['DBInstances'][0]['DBSecurityGroups'].should.equal([])
    conn.create_db_security_group(DBSecurityGroupName='db_sg',
                                  DBSecurityGroupDescription='DB Security Group')
    conn.modify_db_instance(DBInstanceIdentifier='db-master-1',
                            DBSecurityGroups=['db_sg'])
    result = conn.describe_db_instances()
    result['DBInstances'][0]['DBSecurityGroups'][0][
        'DBSecurityGroupName'].should.equal('db_sg')


@disable_on_py3()
@mock_rds2
def test_list_tags_security_group():
    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    security_group = conn.create_db_security_group(DBSecurityGroupName="db_sg",
                                                   DBSecurityGroupDescription='DB Security Group',
                                                   Tags=[{'Value': 'bar',
                                                          'Key': 'foo'},
                                                         {'Value': 'bar1',
                                                          'Key': 'foo1'}])['DBSecurityGroup']['DBSecurityGroupName']
    resource = 'arn:aws:rds:us-west-2:1234567890:secgrp:{0}'.format(
        security_group)
    result = conn.list_tags_for_resource(ResourceName=resource)
    result['TagList'].should.equal([{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])


@disable_on_py3()
@mock_rds2
def test_add_tags_security_group():
    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    security_group = conn.create_db_security_group(DBSecurityGroupName="db_sg",
                                                   DBSecurityGroupDescription='DB Security Group')['DBSecurityGroup']['DBSecurityGroupName']

    resource = 'arn:aws:rds:us-west-2:1234567890:secgrp:{0}'.format(
        security_group)
    conn.add_tags_to_resource(ResourceName=resource,
                              Tags=[{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result['TagList'].should.equal([{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])


@disable_on_py3()
@mock_rds2
def test_remove_tags_security_group():
    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    security_group = conn.create_db_security_group(DBSecurityGroupName="db_sg",
                                                   DBSecurityGroupDescription='DB Security Group',
                                                   Tags=[{'Value': 'bar',
                                                          'Key': 'foo'},
                                                         {'Value': 'bar1',
                                                          'Key': 'foo1'}])['DBSecurityGroup']['DBSecurityGroupName']

    resource = 'arn:aws:rds:us-west-2:1234567890:secgrp:{0}'.format(
        security_group)
    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=['foo'])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result['TagList'].should.equal([{'Value': 'bar1', 'Key': 'foo1'}])


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_create_database_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet1 = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']
    subnet2 = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/26')['Subnet']

    subnet_ids = [subnet1['SubnetId'], subnet2['SubnetId']]
    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.create_db_subnet_group(DBSubnetGroupName='db_subnet',
                                         DBSubnetGroupDescription='my db subnet',
                                         SubnetIds=subnet_ids)
    result['DBSubnetGroup']['DBSubnetGroupName'].should.equal("db_subnet")
    result['DBSubnetGroup'][
        'DBSubnetGroupDescription'].should.equal("my db subnet")
    subnets = result['DBSubnetGroup']['Subnets']
    subnet_group_ids = [subnets[0]['SubnetIdentifier'],
                        subnets[1]['SubnetIdentifier']]
    list(subnet_group_ids).should.equal(subnet_ids)


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_create_database_in_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']

    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_subnet_group(DBSubnetGroupName='db_subnet1',
                                DBSubnetGroupDescription='my db subnet',
                                SubnetIds=[subnet['SubnetId']])
    conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                            AllocatedStorage=10,
                            Engine='postgres',
                            DBInstanceClass='db.m1.small',
                            MasterUsername='root',
                            MasterUserPassword='hunter2',
                            Port=1234,
                            DBSubnetGroupName='db_subnet1')
    result = conn.describe_db_instances(DBInstanceIdentifier='db-master-1')
    result['DBInstances'][0]['DBSubnetGroup'][
        'DBSubnetGroupName'].should.equal('db_subnet1')


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_describe_database_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']

    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_subnet_group(DBSubnetGroupName="db_subnet1",
                                DBSubnetGroupDescription='my db subnet',
                                SubnetIds=[subnet['SubnetId']])
    conn.create_db_subnet_group(DBSubnetGroupName='db_subnet2',
                                DBSubnetGroupDescription='my db subnet',
                                SubnetIds=[subnet['SubnetId']])

    resp = conn.describe_db_subnet_groups()
    resp['DBSubnetGroups'].should.have.length_of(2)

    subnets = resp['DBSubnetGroups'][0]['Subnets']
    subnets.should.have.length_of(1)

    list(conn.describe_db_subnet_groups(DBSubnetGroupName="db_subnet1")
         ['DBSubnetGroups']).should.have.length_of(1)

    conn.describe_db_subnet_groups.when.called_with(
        DBSubnetGroupName="not-a-subnet").should.throw(ClientError)


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_delete_database_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']

    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    conn.create_db_subnet_group(DBSubnetGroupName="db_subnet1",
                                DBSubnetGroupDescription='my db subnet',
                                SubnetIds=[subnet['SubnetId']])
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(1)

    conn.delete_db_subnet_group(DBSubnetGroupName="db_subnet1")
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    conn.delete_db_subnet_group.when.called_with(
        DBSubnetGroupName="db_subnet1").should.throw(ClientError)


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_list_tags_database_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']

    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    subnet = conn.create_db_subnet_group(DBSubnetGroupName="db_subnet1",
                                         DBSubnetGroupDescription='my db subnet',
                                         SubnetIds=[subnet['SubnetId']],
                                         Tags=[{'Value': 'bar',
                                                'Key': 'foo'},
                                               {'Value': 'bar1',
                                                'Key': 'foo1'}])['DBSubnetGroup']['DBSubnetGroupName']
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:subgrp:{0}'.format(subnet))
    result['TagList'].should.equal([{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_add_tags_database_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']

    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    subnet = conn.create_db_subnet_group(DBSubnetGroupName="db_subnet1",
                                         DBSubnetGroupDescription='my db subnet',
                                         SubnetIds=[subnet['SubnetId']],
                                         Tags=[])['DBSubnetGroup']['DBSubnetGroupName']
    resource = 'arn:aws:rds:us-west-2:1234567890:subgrp:{0}'.format(subnet)

    conn.add_tags_to_resource(ResourceName=resource,
                              Tags=[{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result['TagList'].should.equal([{'Value': 'bar',
                                     'Key': 'foo'},
                                    {'Value': 'bar1',
                                     'Key': 'foo1'}])


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_remove_tags_database_subnet_group():
    vpc_conn = boto3.client('ec2', 'us-west-2')
    vpc = vpc_conn.create_vpc(CidrBlock='10.0.0.0/16')['Vpc']
    subnet = vpc_conn.create_subnet(
        VpcId=vpc['VpcId'], CidrBlock='10.1.0.0/24')['Subnet']

    conn = boto3.client('rds', region_name='us-west-2')
    result = conn.describe_db_subnet_groups()
    result['DBSubnetGroups'].should.have.length_of(0)

    subnet = conn.create_db_subnet_group(DBSubnetGroupName="db_subnet1",
                                         DBSubnetGroupDescription='my db subnet',
                                         SubnetIds=[subnet['SubnetId']],
                                         Tags=[{'Value': 'bar',
                                                'Key': 'foo'},
                                               {'Value': 'bar1',
                                                'Key': 'foo1'}])['DBSubnetGroup']['DBSubnetGroupName']
    resource = 'arn:aws:rds:us-west-2:1234567890:subgrp:{0}'.format(subnet)

    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=['foo'])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result['TagList'].should.equal([{'Value': 'bar1', 'Key': 'foo1'}])


@disable_on_py3()
@mock_rds2
def test_create_database_replica():
    conn = boto3.client('rds', region_name='us-west-2')

    database = conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                                       AllocatedStorage=10,
                                       Engine='postgres',
                                       DBInstanceClass='db.m1.small',
                                       MasterUsername='root',
                                       MasterUserPassword='hunter2',
                                       Port=1234,
                                       DBSecurityGroups=["my_sg"])

    replica = conn.create_db_instance_read_replica(DBInstanceIdentifier="db-replica-1",
                                                   SourceDBInstanceIdentifier="db-master-1",
                                                   DBInstanceClass="db.m1.small")
    replica['DBInstance'][
        'ReadReplicaSourceDBInstanceIdentifier'].should.equal('db-master-1')
    replica['DBInstance']['DBInstanceClass'].should.equal('db.m1.small')
    replica['DBInstance']['DBInstanceIdentifier'].should.equal('db-replica-1')

    master = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    master['DBInstances'][0]['ReadReplicaDBInstanceIdentifiers'].should.equal([
                                                                              'db-replica-1'])

    conn.delete_db_instance(
        DBInstanceIdentifier="db-replica-1", SkipFinalSnapshot=True)

    master = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    master['DBInstances'][0][
        'ReadReplicaDBInstanceIdentifiers'].should.equal([])


@disable_on_py3()
@mock_rds2
@mock_kms
def test_create_database_with_encrypted_storage():
    kms_conn = boto3.client('kms', region_name='us-west-2')
    key = kms_conn.create_key(Policy='my RDS encryption policy',
                              Description='RDS encryption key',
                              KeyUsage='ENCRYPT_DECRYPT')

    conn = boto3.client('rds', region_name='us-west-2')
    database = conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                                       AllocatedStorage=10,
                                       Engine='postgres',
                                       DBInstanceClass='db.m1.small',
                                       MasterUsername='root',
                                       MasterUserPassword='hunter2',
                                       Port=1234,
                                       DBSecurityGroups=["my_sg"],
                                       StorageEncrypted=True,
                                       KmsKeyId=key['KeyMetadata']['KeyId'])

    database['DBInstance']['StorageEncrypted'].should.equal(True)
    database['DBInstance']['KmsKeyId'].should.equal(
        key['KeyMetadata']['KeyId'])


@disable_on_py3()
@mock_rds2
def test_create_db_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    db_parameter_group = conn.create_db_parameter_group(DBParameterGroupName='test',
                                                        DBParameterGroupFamily='mysql5.6',
                                                        Description='test parameter group')

    db_parameter_group['DBParameterGroup'][
        'DBParameterGroupName'].should.equal('test')
    db_parameter_group['DBParameterGroup'][
        'DBParameterGroupFamily'].should.equal('mysql5.6')
    db_parameter_group['DBParameterGroup'][
        'Description'].should.equal('test parameter group')


@disable_on_py3()
@mock_rds2
def test_create_db_instance_with_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    db_parameter_group = conn.create_db_parameter_group(DBParameterGroupName='test',
                                                        DBParameterGroupFamily='mysql5.6',
                                                        Description='test parameter group')

    database = conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                                       AllocatedStorage=10,
                                       Engine='mysql',
                                       DBInstanceClass='db.m1.small',
                                       DBParameterGroupName='test',
                                       MasterUsername='root',
                                       MasterUserPassword='hunter2',
                                       Port=1234)

    len(database['DBInstance']['DBParameterGroups']).should.equal(1)
    database['DBInstance']['DBParameterGroups'][0][
        'DBParameterGroupName'].should.equal('test')
    database['DBInstance']['DBParameterGroups'][0][
        'ParameterApplyStatus'].should.equal('in-sync')


@disable_on_py3()
@mock_rds2
def test_modify_db_instance_with_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    database = conn.create_db_instance(DBInstanceIdentifier='db-master-1',
                                       AllocatedStorage=10,
                                       Engine='mysql',
                                       DBInstanceClass='db.m1.small',
                                       MasterUsername='root',
                                       MasterUserPassword='hunter2',
                                       Port=1234)

    len(database['DBInstance']['DBParameterGroups']).should.equal(1)
    database['DBInstance']['DBParameterGroups'][0][
        'DBParameterGroupName'].should.equal('default.mysql5.6')
    database['DBInstance']['DBParameterGroups'][0][
        'ParameterApplyStatus'].should.equal('in-sync')

    db_parameter_group = conn.create_db_parameter_group(DBParameterGroupName='test',
                                                        DBParameterGroupFamily='mysql5.6',
                                                        Description='test parameter group')
    conn.modify_db_instance(DBInstanceIdentifier='db-master-1',
                            DBParameterGroupName='test',
                            ApplyImmediately=True)

    database = conn.describe_db_instances(
        DBInstanceIdentifier='db-master-1')['DBInstances'][0]
    len(database['DBParameterGroups']).should.equal(1)
    database['DBParameterGroups'][0][
        'DBParameterGroupName'].should.equal('test')
    database['DBParameterGroups'][0][
        'ParameterApplyStatus'].should.equal('in-sync')


@disable_on_py3()
@mock_rds2
def test_create_db_parameter_group_empty_description():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_parameter_group.when.called_with(DBParameterGroupName='test',
                                                    DBParameterGroupFamily='mysql5.6',
                                                    Description='').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_create_db_parameter_group_duplicate():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_parameter_group(DBParameterGroupName='test',
                                   DBParameterGroupFamily='mysql5.6',
                                   Description='test parameter group')
    conn.create_db_parameter_group.when.called_with(DBParameterGroupName='test',
                                                    DBParameterGroupFamily='mysql5.6',
                                                    Description='test parameter group').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_describe_db_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_parameter_group(DBParameterGroupName='test',
                                   DBParameterGroupFamily='mysql5.6',
                                   Description='test parameter group')
    db_parameter_groups = conn.describe_db_parameter_groups(
        DBParameterGroupName='test')
    db_parameter_groups['DBParameterGroups'][0][
        'DBParameterGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_db_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    db_parameter_groups = conn.describe_db_parameter_groups(
        DBParameterGroupName='test')
    len(db_parameter_groups['DBParameterGroups']).should.equal(0)


@disable_on_py3()
@mock_rds2
def test_delete_db_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_parameter_group(DBParameterGroupName='test',
                                   DBParameterGroupFamily='mysql5.6',
                                   Description='test parameter group')
    db_parameter_groups = conn.describe_db_parameter_groups(
        DBParameterGroupName='test')
    db_parameter_groups['DBParameterGroups'][0][
        'DBParameterGroupName'].should.equal('test')
    conn.delete_db_parameter_group(DBParameterGroupName='test')
    db_parameter_groups = conn.describe_db_parameter_groups(
        DBParameterGroupName='test')
    len(db_parameter_groups['DBParameterGroups']).should.equal(0)


@disable_on_py3()
@mock_rds2
def test_modify_db_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_parameter_group(DBParameterGroupName='test',
                                   DBParameterGroupFamily='mysql5.6',
                                   Description='test parameter group')

    modify_result = conn.modify_db_parameter_group(DBParameterGroupName='test',
                                                   Parameters=[{
                                                       'ParameterName': 'foo',
                                                       'ParameterValue': 'foo_val',
                                                       'Description': 'test param',
                                                       'ApplyMethod': 'immediate'
                                                   }]
                                                   )

    modify_result['DBParameterGroupName'].should.equal('test')

    db_parameters = conn.describe_db_parameters(DBParameterGroupName='test')
    db_parameters['Parameters'][0]['ParameterName'].should.equal('foo')
    db_parameters['Parameters'][0]['ParameterValue'].should.equal('foo_val')
    db_parameters['Parameters'][0]['Description'].should.equal('test param')
    db_parameters['Parameters'][0]['ApplyMethod'].should.equal('immediate')


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_db_parameter_group():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.delete_db_parameter_group.when.called_with(
        DBParameterGroupName='non-existant').should.throw(ClientError)


@disable_on_py3()
@mock_rds2
def test_create_parameter_group_with_tags():
    conn = boto3.client('rds', region_name='us-west-2')
    conn.create_db_parameter_group(DBParameterGroupName='test',
                                   DBParameterGroupFamily='mysql5.6',
                                   Description='test parameter group',
                                   Tags=[{
                                       'Key': 'foo',
                                       'Value': 'bar',
                                   }])
    result = conn.list_tags_for_resource(
        ResourceName='arn:aws:rds:us-west-2:1234567890:pg:test')
    result['TagList'].should.equal([{'Value': 'bar', 'Key': 'foo'}])
