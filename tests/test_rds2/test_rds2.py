from __future__ import unicode_literals

import boto.rds2
import boto.vpc
from boto.exception import BotoServerError
import sure  # noqa
from moto import mock_ec2, mock_rds2
from tests.helpers import disable_on_py3


@disable_on_py3()
@mock_rds2
def test_create_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    database = conn.create_db_instance(db_instance_identifier='db-master-1',
                                       allocated_storage=10,
                                       engine='postgres',
                                       db_instance_class='db.m1.small',
                                       master_username='root',
                                       master_user_password='hunter2',
                                       db_security_groups=["my_sg"])
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBInstanceStatus'].should.equal('available')
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBInstanceIdentifier'].should.equal("db-master-1")
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['AllocatedStorage'].should.equal('10')
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBInstanceClass'].should.equal("db.m1.small")
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['MasterUsername'].should.equal("root")
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBSecurityGroups'][0]['DBSecurityGroup']['DBSecurityGroupName'].should.equal('my_sg')


@disable_on_py3()
@mock_rds2
def test_get_databases():
    conn = boto.rds2.connect_to_region("us-west-2")

    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(0)

    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    conn.create_db_instance(db_instance_identifier='db-master-2',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(2)

    instances = conn.describe_db_instances("db-master-1")
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(1)
    instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['DBInstanceIdentifier'].should.equal("db-master-1")


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.describe_db_instances.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_modify_db_instance():
    conn = boto.rds2.connect_to_region("us-west-2")
    database = conn.create_db_instance(db_instance_identifier='db-master-1',
                                       allocated_storage=10,
                                       engine='postgres',
                                       db_instance_class='db.m1.small',
                                       master_username='root',
                                       master_user_password='hunter2',
                                       db_security_groups=["my_sg"])
    instances = conn.describe_db_instances('db-master-1')
    instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['AllocatedStorage'].should.equal('10')
    conn.modify_db_instance(db_instance_identifier='db-master-1', allocated_storage=20, apply_immediately=True)
    instances = conn.describe_db_instances('db-master-1')
    instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['AllocatedStorage'].should.equal('20')


@disable_on_py3()
@mock_rds2
def test_modify_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.modify_db_instance.when.called_with(db_instance_identifier='not-a-db',
                                             allocated_storage=20,
                                             apply_immediately=True).should.throw(BotoServerError)

@disable_on_py3()
@mock_rds2
def test_reboot_db_instance():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    database = conn.reboot_db_instance('db-master-1')
    database['RebootDBInstanceResponse']['RebootDBInstanceResult']['DBInstance']['DBInstanceIdentifier'].should.equal("db-master-1")


@disable_on_py3()
@mock_rds2
def test_reboot_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.reboot_db_instance.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(0)
    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(1)

    conn.delete_db_instance("db-master-1")
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(0)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_db_instance.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    option_group = conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['OptionGroupName'].should.equal('test')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['EngineName'].should.equal('mysql')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['OptionGroupDescription'].should.equal('test option group')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['MajorEngineVersion'].should.equal('5.6')


@disable_on_py3()
@mock_rds2
def test_create_option_group_bad_engine_name():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group.when.called_with('test', 'invalid_engine', '5.6', 'test invalid engine').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_bad_engine_major_version():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group.when.called_with('test', 'mysql', '6.6.6', 'test invalid engine version').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_empty_description():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group.when.called_with('test', 'mysql', '5.6', '').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_duplicate():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    conn.create_option_group.when.called_with('test', 'mysql', '5.6', 'foo').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_describe_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    option_groups = conn.describe_option_groups('test')
    option_groups['DescribeOptionGroupsResponse']['DescribeOptionGroupsResult']['OptionGroupsList'][0]['OptionGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.describe_option_groups.when.called_with("not-a-option-group").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    option_groups = conn.describe_option_groups('test')
    option_groups['DescribeOptionGroupsResponse']['DescribeOptionGroupsResult']['OptionGroupsList'][0]['OptionGroupName'].should.equal('test')
    conn.delete_option_group('test')
    conn.describe_option_groups.when.called_with('test').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_option_group.when.called_with('non-existant').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_describe_option_group_options():
    conn = boto.rds2.connect_to_region("us-west-2")
    option_group_options = conn.describe_option_group_options('sqlserver-ee')
    len(option_group_options['DescribeOptionGroupOptionsResponse']['DescribeOptionGroupOptionsResult']['OptionGroupOptions']).should.equal(4)
    option_group_options = conn.describe_option_group_options('sqlserver-ee', '11.00')
    len(option_group_options['DescribeOptionGroupOptionsResponse']['DescribeOptionGroupOptionsResult']['OptionGroupOptions']).should.equal(2)
    option_group_options = conn.describe_option_group_options('mysql', '5.6')
    len(option_group_options['DescribeOptionGroupOptionsResponse']['DescribeOptionGroupOptionsResult']['OptionGroupOptions']).should.equal(1)
    conn.describe_option_group_options.when.called_with('non-existent').should.throw(BotoServerError)
    conn.describe_option_group_options.when.called_with('mysql', 'non-existent').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_modify_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    # TODO: create option and validate before deleting.
    # if Someone can tell me how the hell to use this function
    # to add options to an option_group, I can finish coding this.
    result = conn.modify_option_group('test', [], ['MEMCACHED'], True)
    result['ModifyOptionGroupResponse']['ModifyOptionGroupResult']['EngineName'].should.equal('mysql')
    result['ModifyOptionGroupResponse']['ModifyOptionGroupResult']['Options'].should.equal([])
    result['ModifyOptionGroupResponse']['ModifyOptionGroupResult']['OptionGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_modify_option_group_no_options():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    conn.modify_option_group.when.called_with('test').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_modify_non_existant_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.modify_option_group.when.called_with('non-existant', [('OptionName', 'Port', 'DBSecurityGroupMemberships', 'VpcSecurityGroupMemberships', 'OptionSettings')]).should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_db_instance.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_list_tags_invalid_arn():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.list_tags_for_resource.when.called_with('arn:aws:rds:bad-arn').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_list_tags_db():
    conn = boto.rds2.connect_to_region("us-west-2")
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:foo')
    result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList'].should.equal([])
    conn.create_db_instance(db_instance_identifier='db-with-tags',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"],
                            tags=[('foo', 'bar'), ('foo1', 'bar1')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:db-with-tags')
    result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList'].should.equal([{'Value': 'bar',
                                                                                                 'Key': 'foo'},
                                                                                                {'Value': 'bar1',
                                                                                                 'Key': 'foo1'}])


@disable_on_py3()
@mock_rds2
def test_add_tags_db():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_db_instance(db_instance_identifier='db-without-tags',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"],
                            tags=[('foo', 'bar'), ('foo1', 'bar1')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:db-without-tags')
    list(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.have.length_of(2)
    conn.add_tags_to_resource('arn:aws:rds:us-west-2:1234567890:db:db-without-tags',
                              [('foo', 'fish'), ('foo2', 'bar2')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:db-without-tags')
    list(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.have.length_of(3)


@disable_on_py3()
@mock_rds2
def test_remove_tags_db():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_db_instance(db_instance_identifier='db-with-tags',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"],
                            tags=[('foo', 'bar'), ('foo1', 'bar1')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:db-with-tags')
    len(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.equal(2)
    conn.remove_tags_from_resource('arn:aws:rds:us-west-2:1234567890:db:db-with-tags', ['foo'])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:db-with-tags')
    len(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.equal(1)


@disable_on_py3()
@mock_rds2
def test_add_tags_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.have.length_of(0)
    conn.add_tags_to_resource('arn:aws:rds:us-west-2:1234567890:og:test',
                                       [('foo', 'fish'), ('foo2', 'bar2')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.have.length_of(2)


@disable_on_py3()
@mock_rds2
def test_remove_tags_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    conn.add_tags_to_resource('arn:aws:rds:us-west-2:1234567890:og:test',
                                       [('foo', 'fish'), ('foo2', 'bar2')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.have.length_of(2)
    conn.remove_tags_from_resource('arn:aws:rds:us-west-2:1234567890:og:test',
                                 ['foo'])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:og:test')
    list(result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList']).should.have.length_of(1)


@disable_on_py3()
@mock_rds2
def test_create_database_security_group():
    conn = boto.rds2.connect_to_region("us-west-2")

    result = conn.create_db_security_group('db_sg', 'DB Security Group')
    result['CreateDBSecurityGroupResponse']['CreateDBSecurityGroupResult']['DBSecurityGroup']['DBSecurityGroupName'].should.equal("db_sg")
    result['CreateDBSecurityGroupResponse']['CreateDBSecurityGroupResult']['DBSecurityGroup']['DBSecurityGroupDescription'].should.equal("DB Security Group")
    result['CreateDBSecurityGroupResponse']['CreateDBSecurityGroupResult']['DBSecurityGroup']['IPRanges'].should.equal([])


@disable_on_py3()
@mock_rds2
def test_get_security_groups():
    conn = boto.rds2.connect_to_region("us-west-2")

    result = conn.describe_db_security_groups()
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'].should.have.length_of(0)

    conn.create_db_security_group('db_sg1', 'DB Security Group')
    conn.create_db_security_group('db_sg2', 'DB Security Group')

    result = conn.describe_db_security_groups()
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'].should.have.length_of(2)

    result = conn.describe_db_security_groups("db_sg1")
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'].should.have.length_of(1)
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'][0]['DBSecurityGroupName'].should.equal("db_sg1")


@disable_on_py3()
@mock_rds2
def test_get_non_existant_security_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.describe_db_security_groups.when.called_with("not-a-sg").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_database_security_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_db_security_group('db_sg', 'DB Security Group')

    result = conn.describe_db_security_groups()
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'].should.have.length_of(1)

    conn.delete_db_security_group("db_sg")
    result = conn.describe_db_security_groups()
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'].should.have.length_of(0)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_security_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_db_security_group.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_security_group_authorize():
    conn = boto.rds2.connect_to_region("us-west-2")
    security_group = conn.create_db_security_group('db_sg', 'DB Security Group')
    security_group['CreateDBSecurityGroupResponse']['CreateDBSecurityGroupResult']['DBSecurityGroup']['IPRanges'].should.equal([])


    conn.authorize_db_security_group_ingress(db_security_group_name='db_sg',
                                             cidrip='10.3.2.45/32')

    result = conn.describe_db_security_groups("db_sg")
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'][0]['IPRanges'].should.have.length_of(1)
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'][0]['IPRanges'].should.equal(['10.3.2.45/32'])

    conn.authorize_db_security_group_ingress(db_security_group_name='db_sg',
                                             cidrip='10.3.2.46/32')
    result = conn.describe_db_security_groups("db_sg")
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'][0]['IPRanges'].should.have.length_of(2)
    result['DescribeDBSecurityGroupsResponse']['DescribeDBSecurityGroupsResult']['DBSecurityGroups'][0]['IPRanges'].should.equal(['10.3.2.45/32', '10.3.2.46/32'])


@disable_on_py3()
@mock_rds2
def test_add_security_group_to_database():
    conn = boto.rds2.connect_to_region("us-west-2")

    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2')
    result = conn.describe_db_instances()
    result['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['DBSecurityGroups'].should.equal([])
    conn.create_db_security_group('db_sg', 'DB Security Group')
    conn.modify_db_instance(db_instance_identifier='db-master-1',
                            db_security_groups=['db_sg'])
    result = conn.describe_db_instances()
    result['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['DBSecurityGroups'][0]['DBSecurityGroup']['DBSecurityGroupName'].should.equal('db_sg')


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_create_database_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet1 = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")
    subnet2 = vpc_conn.create_subnet(vpc.id, "10.2.0.0/24")

    subnet_ids = [subnet1.id, subnet2.id]
    conn = boto.rds2.connect_to_region("us-west-2")
    result = conn.create_db_subnet_group("db_subnet", "my db subnet", subnet_ids)
    result['CreateDBSubnetGroupResponse']['CreateDBSubnetGroupResult']['DBSubnetGroup']['DBSubnetGroupName'].should.equal("db_subnet")
    result['CreateDBSubnetGroupResponse']['CreateDBSubnetGroupResult']['DBSubnetGroup']['DBSubnetGroupDescription'].should.equal("my db subnet")
    subnets = result['CreateDBSubnetGroupResponse']['CreateDBSubnetGroupResult']['DBSubnetGroup']['Subnets']
    subnet_group_ids = [subnets['Subnet'][0]['SubnetIdentifier'], subnets['Subnet'][1]['SubnetIdentifier']]
    list(subnet_group_ids).should.equal(subnet_ids)


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_create_database_in_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_subnet_group_name='db_subnet1')
    result = conn.describe_db_instances("db-master-1")
    result['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['DBSubnetGroup']['DBSubnetGroupName'].should.equal("db_subnet1")


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_describe_database_subnet_group():
   vpc_conn = boto.vpc.connect_to_region("us-west-2")
   vpc = vpc_conn.create_vpc("10.0.0.0/16")
   subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

   conn = boto.rds2.connect_to_region("us-west-2")
   conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
   conn.create_db_subnet_group("db_subnet2", "my db subnet", [subnet.id])

   resp = conn.describe_db_subnet_groups()
   groups_resp = resp['DescribeDBSubnetGroupsResponse']

   subnet_groups = groups_resp['DescribeDBSubnetGroupsResult']['DBSubnetGroups']
   subnet_groups.should.have.length_of(2)

   subnets = groups_resp['DescribeDBSubnetGroupsResult']['DBSubnetGroups'][0]['DBSubnetGroup']['Subnets']
   subnets.should.have.length_of(1)

   list(resp).should.have.length_of(1)
   list(groups_resp).should.have.length_of(2)
   list(conn.describe_db_subnet_groups("db_subnet1")).should.have.length_of(1)

   conn.describe_db_subnet_groups.when.called_with("not-a-subnet").should.throw(BotoServerError)


@disable_on_py3()
@mock_ec2
@mock_rds2
def test_delete_database_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

    conn = boto.rds2.connect_to_region("us-west-2")
    result = conn.describe_db_subnet_groups()
    result['DescribeDBSubnetGroupsResponse']['DescribeDBSubnetGroupsResult']['DBSubnetGroups'].should.have.length_of(0)

    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
    result = conn.describe_db_subnet_groups()
    result['DescribeDBSubnetGroupsResponse']['DescribeDBSubnetGroupsResult']['DBSubnetGroups'].should.have.length_of(1)

    conn.delete_db_subnet_group("db_subnet1")
    result = conn.describe_db_subnet_groups()
    result['DescribeDBSubnetGroupsResponse']['DescribeDBSubnetGroupsResult']['DBSubnetGroups'].should.have.length_of(0)

    conn.delete_db_subnet_group.when.called_with("db_subnet1").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_database_replica():
    conn = boto.rds2.connect_to_region("us-west-2")

    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])

    replica = conn.create_db_instance_read_replica("db-replica-1", "db-master-1", "db.m1.small")
    replica['CreateDBInstanceReadReplicaResponse']['CreateDBInstanceReadReplicaResult']['DBInstance']['ReadReplicaSourceDBInstanceIdentifier'].should.equal('db-master-1')
    replica['CreateDBInstanceReadReplicaResponse']['CreateDBInstanceReadReplicaResult']['DBInstance']['DBInstanceClass'].should.equal('db.m1.small')
    replica['CreateDBInstanceReadReplicaResponse']['CreateDBInstanceReadReplicaResult']['DBInstance']['DBInstanceIdentifier'].should.equal('db-replica-1')

    master = conn.describe_db_instances("db-master-1")
    master['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['ReadReplicaDBInstanceIdentifiers'].should.equal(['db-replica-1'])

    conn.delete_db_instance("db-replica-1")

    master = conn.describe_db_instances("db-master-1")
    master['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['ReadReplicaDBInstanceIdentifiers'].should.equal([])
