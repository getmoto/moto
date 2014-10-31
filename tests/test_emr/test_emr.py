from __future__ import unicode_literals
import boto
from boto.emr.instance_group import InstanceGroup
from boto.emr.step import StreamingStep
import sure  # noqa

from moto import mock_emr
from tests.helpers import requires_boto_gte


@mock_emr
def test_create_job_flow():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    step2 = StreamingStep(
        name='My wordcount example2',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input2',
        output='s3n://output_bucket/output/wordcount_output2'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        master_instance_type='m1.medium',
        slave_instance_type='m1.small',
        steps=[step1, step2],
    )

    job_flow = conn.describe_jobflow(job_id)
    job_flow.state.should.equal('STARTING')
    job_flow.jobflowid.should.equal(job_id)
    job_flow.name.should.equal('My jobflow')
    job_flow.masterinstancetype.should.equal('m1.medium')
    job_flow.slaveinstancetype.should.equal('m1.small')
    job_flow.loguri.should.equal('s3://some_bucket/jobflow_logs')
    job_flow.visibletoallusers.should.equal('False')
    int(job_flow.normalizedinstancehours).should.equal(0)
    job_step = job_flow.steps[0]
    job_step.name.should.equal('My wordcount example')
    job_step.state.should.equal('STARTING')
    args = [arg.value for arg in job_step.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input',
        '-output',
        's3n://output_bucket/output/wordcount_output',
    ])

    job_step2 = job_flow.steps[1]
    job_step2.name.should.equal('My wordcount example2')
    job_step2.state.should.equal('PENDING')
    args = [arg.value for arg in job_step2.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input2',
        '-output',
        's3n://output_bucket/output/wordcount_output2',
    ])


@requires_boto_gte("2.8")
@mock_emr
def test_create_job_flow_with_new_params():
    # Test that run_jobflow works with newer params
    conn = boto.connect_emr()

    conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        master_instance_type='m1.medium',
        slave_instance_type='m1.small',
        job_flow_role='some-role-arn',
        steps=[],
    )


@requires_boto_gte("2.8")
@mock_emr
def test_create_job_flow_visible_to_all_users():
    conn = boto.connect_emr()

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[],
        visible_to_all_users=True,
    )
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('True')


@mock_emr
def test_terminate_job_flow():
    conn = boto.connect_emr()
    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[]
    )

    flow = conn.describe_jobflows()[0]
    flow.state.should.equal('STARTING')
    conn.terminate_jobflow(job_id)
    flow = conn.describe_jobflows()[0]
    flow.state.should.equal('TERMINATED')


@mock_emr
def test_add_steps_to_flow():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[step1]
    )

    job_flow = conn.describe_jobflow(job_id)
    job_flow.state.should.equal('STARTING')
    job_flow.jobflowid.should.equal(job_id)
    job_flow.name.should.equal('My jobflow')
    job_flow.loguri.should.equal('s3://some_bucket/jobflow_logs')

    step2 = StreamingStep(
        name='My wordcount example2',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input2',
        output='s3n://output_bucket/output/wordcount_output2'
    )

    conn.add_jobflow_steps(job_id, [step2])

    job_flow = conn.describe_jobflow(job_id)
    job_step = job_flow.steps[0]
    job_step.name.should.equal('My wordcount example')
    job_step.state.should.equal('STARTING')
    args = [arg.value for arg in job_step.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input',
        '-output',
        's3n://output_bucket/output/wordcount_output',
    ])

    job_step2 = job_flow.steps[1]
    job_step2.name.should.equal('My wordcount example2')
    job_step2.state.should.equal('PENDING')
    args = [arg.value for arg in job_step2.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input2',
        '-output',
        's3n://output_bucket/output/wordcount_output2',
    ])


@mock_emr
def test_create_instance_groups():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[step1],
    )

    instance_group = InstanceGroup(6, 'TASK', 'c1.medium', 'SPOT', 'spot-0.07', '0.07')
    instance_group = conn.add_instance_groups(job_id, [instance_group])
    instance_group_id = instance_group.instancegroupids
    job_flow = conn.describe_jobflows()[0]
    int(job_flow.instancecount).should.equal(6)
    instance_group = job_flow.instancegroups[0]
    instance_group.instancegroupid.should.equal(instance_group_id)
    int(instance_group.instancerunningcount).should.equal(6)
    instance_group.instancerole.should.equal('TASK')
    instance_group.instancetype.should.equal('c1.medium')
    instance_group.market.should.equal('SPOT')
    instance_group.name.should.equal('spot-0.07')
    instance_group.bidprice.should.equal('0.07')


@mock_emr
def test_modify_instance_groups():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[step1]
    )

    instance_group1 = InstanceGroup(6, 'TASK', 'c1.medium', 'SPOT', 'spot-0.07', '0.07')
    instance_group2 = InstanceGroup(6, 'TASK', 'c1.medium', 'SPOT', 'spot-0.07', '0.07')
    instance_group = conn.add_instance_groups(job_id, [instance_group1, instance_group2])
    instance_group_ids = instance_group.instancegroupids.split(",")

    job_flow = conn.describe_jobflows()[0]
    int(job_flow.instancecount).should.equal(12)
    instance_group = job_flow.instancegroups[0]
    int(instance_group.instancerunningcount).should.equal(6)

    conn.modify_instance_groups(instance_group_ids, [2, 3])

    job_flow = conn.describe_jobflows()[0]
    int(job_flow.instancecount).should.equal(5)
    instance_group1 = [
        group for group
        in job_flow.instancegroups
        if group.instancegroupid == instance_group_ids[0]
    ][0]
    int(instance_group1.instancerunningcount).should.equal(2)
    instance_group2 = [
        group for group
        in job_flow.instancegroups
        if group.instancegroupid == instance_group_ids[1]
    ][0]
    int(instance_group2.instancerunningcount).should.equal(3)


@requires_boto_gte("2.8")
@mock_emr
def test_set_visible_to_all_users():
    conn = boto.connect_emr()

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[],
        visible_to_all_users=False,
    )
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('False')

    conn.set_visible_to_all_users(job_id, True)

    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('True')

    conn.set_visible_to_all_users(job_id, False)

    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('False')
