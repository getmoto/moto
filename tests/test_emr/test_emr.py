from __future__ import unicode_literals
import time
from datetime import datetime

import boto
import pytz
from boto.emr.bootstrap_action import BootstrapAction
from boto.emr.instance_group import InstanceGroup
from boto.emr.step import StreamingStep

import six
import sure  # noqa

from moto import mock_emr_deprecated
from tests.helpers import requires_boto_gte


run_jobflow_args = dict(
    job_flow_role="EMR_EC2_DefaultRole",
    keep_alive=True,
    log_uri="s3://some_bucket/jobflow_logs",
    master_instance_type="c1.medium",
    name="My jobflow",
    num_instances=2,
    service_role="EMR_DefaultRole",
    slave_instance_type="c1.medium",
)


input_instance_groups = [
    InstanceGroup(1, "MASTER", "c1.medium", "ON_DEMAND", "master"),
    InstanceGroup(3, "CORE", "c1.medium", "ON_DEMAND", "core"),
    InstanceGroup(6, "TASK", "c1.large", "SPOT", "task-1", "0.07"),
    InstanceGroup(10, "TASK", "c1.xlarge", "SPOT", "task-2", "0.05"),
]


@mock_emr_deprecated
def test_describe_cluster():
    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    args.update(
        dict(
            api_params={
                "Applications.member.1.Name": "Spark",
                "Applications.member.1.Version": "2.4.2",
                "Configurations.member.1.Classification": "yarn-site",
                "Configurations.member.1.Properties.entry.1.key": "someproperty",
                "Configurations.member.1.Properties.entry.1.value": "somevalue",
                "Configurations.member.1.Properties.entry.2.key": "someotherproperty",
                "Configurations.member.1.Properties.entry.2.value": "someothervalue",
                "Instances.EmrManagedMasterSecurityGroup": "master-security-group",
                "Instances.Ec2SubnetId": "subnet-8be41cec",
            },
            availability_zone="us-east-2b",
            ec2_keyname="mykey",
            job_flow_role="EMR_EC2_DefaultRole",
            keep_alive=False,
            log_uri="s3://some_bucket/jobflow_logs",
            name="My jobflow",
            service_role="EMR_DefaultRole",
            visible_to_all_users=True,
        )
    )
    cluster_id = conn.run_jobflow(**args)
    input_tags = {"tag1": "val1", "tag2": "val2"}
    conn.add_tags(cluster_id, input_tags)

    cluster = conn.describe_cluster(cluster_id)
    cluster.applications[0].name.should.equal("Spark")
    cluster.applications[0].version.should.equal("2.4.2")
    cluster.autoterminate.should.equal("true")

    # configurations appear not be supplied as attributes?

    attrs = cluster.ec2instanceattributes
    # AdditionalMasterSecurityGroups
    # AdditionalSlaveSecurityGroups
    attrs.ec2availabilityzone.should.equal(args["availability_zone"])
    attrs.ec2keyname.should.equal(args["ec2_keyname"])
    attrs.ec2subnetid.should.equal(args["api_params"]["Instances.Ec2SubnetId"])
    # EmrManagedMasterSecurityGroups
    # EmrManagedSlaveSecurityGroups
    attrs.iaminstanceprofile.should.equal(args["job_flow_role"])
    # ServiceAccessSecurityGroup

    cluster.id.should.equal(cluster_id)
    cluster.loguri.should.equal(args["log_uri"])
    cluster.masterpublicdnsname.should.be.a(six.string_types)
    cluster.name.should.equal(args["name"])
    int(cluster.normalizedinstancehours).should.equal(0)
    # cluster.release_label
    cluster.shouldnt.have.property("requestedamiversion")
    cluster.runningamiversion.should.equal("1.0.0")
    # cluster.securityconfiguration
    cluster.servicerole.should.equal(args["service_role"])

    cluster.status.state.should.equal("TERMINATED")
    cluster.status.statechangereason.message.should.be.a(six.string_types)
    cluster.status.statechangereason.code.should.be.a(six.string_types)
    cluster.status.timeline.creationdatetime.should.be.a(six.string_types)
    # cluster.status.timeline.enddatetime.should.be.a(six.string_types)
    # cluster.status.timeline.readydatetime.should.be.a(six.string_types)

    dict((item.key, item.value) for item in cluster.tags).should.equal(input_tags)

    cluster.terminationprotected.should.equal("false")
    cluster.visibletoallusers.should.equal("true")


@mock_emr_deprecated
def test_describe_jobflows():
    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    expected = {}

    for idx in range(4):
        cluster_name = "cluster" + str(idx)
        args["name"] = cluster_name
        cluster_id = conn.run_jobflow(**args)
        expected[cluster_id] = {
            "id": cluster_id,
            "name": cluster_name,
            "state": "WAITING",
        }

    # need sleep since it appears the timestamp is always rounded to
    # the nearest second internally
    time.sleep(1)
    timestamp = datetime.now(pytz.utc)
    time.sleep(1)

    for idx in range(4, 6):
        cluster_name = "cluster" + str(idx)
        args["name"] = cluster_name
        cluster_id = conn.run_jobflow(**args)
        conn.terminate_jobflow(cluster_id)
        expected[cluster_id] = {
            "id": cluster_id,
            "name": cluster_name,
            "state": "TERMINATED",
        }
    jobs = conn.describe_jobflows()
    jobs.should.have.length_of(6)

    for cluster_id, y in expected.items():
        resp = conn.describe_jobflows(jobflow_ids=[cluster_id])
        resp.should.have.length_of(1)
        resp[0].jobflowid.should.equal(cluster_id)

    resp = conn.describe_jobflows(states=["WAITING"])
    resp.should.have.length_of(4)
    for x in resp:
        x.state.should.equal("WAITING")

    resp = conn.describe_jobflows(created_before=timestamp)
    resp.should.have.length_of(4)

    resp = conn.describe_jobflows(created_after=timestamp)
    resp.should.have.length_of(2)


@mock_emr_deprecated
def test_describe_jobflow():
    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    args.update(
        dict(
            ami_version="3.8.1",
            api_params={
                #'Applications.member.1.Name': 'Spark',
                #'Applications.member.1.Version': '2.4.2',
                #'Configurations.member.1.Classification': 'yarn-site',
                #'Configurations.member.1.Properties.entry.1.key': 'someproperty',
                #'Configurations.member.1.Properties.entry.1.value': 'somevalue',
                #'Instances.EmrManagedMasterSecurityGroup': 'master-security-group',
                "Instances.Ec2SubnetId": "subnet-8be41cec"
            },
            ec2_keyname="mykey",
            hadoop_version="2.4.0",
            name="My jobflow",
            log_uri="s3://some_bucket/jobflow_logs",
            keep_alive=True,
            master_instance_type="c1.medium",
            slave_instance_type="c1.medium",
            num_instances=2,
            availability_zone="us-west-2b",
            job_flow_role="EMR_EC2_DefaultRole",
            service_role="EMR_DefaultRole",
            visible_to_all_users=True,
        )
    )

    cluster_id = conn.run_jobflow(**args)
    jf = conn.describe_jobflow(cluster_id)
    jf.amiversion.should.equal(args["ami_version"])
    jf.bootstrapactions.should.equal(None)
    jf.creationdatetime.should.be.a(six.string_types)
    jf.should.have.property("laststatechangereason")
    jf.readydatetime.should.be.a(six.string_types)
    jf.startdatetime.should.be.a(six.string_types)
    jf.state.should.equal("WAITING")

    jf.ec2keyname.should.equal(args["ec2_keyname"])
    # Ec2SubnetId
    jf.hadoopversion.should.equal(args["hadoop_version"])
    int(jf.instancecount).should.equal(2)

    for ig in jf.instancegroups:
        ig.creationdatetime.should.be.a(six.string_types)
        # ig.enddatetime.should.be.a(six.string_types)
        ig.should.have.property("instancegroupid").being.a(six.string_types)
        int(ig.instancerequestcount).should.equal(1)
        ig.instancerole.should.be.within(["MASTER", "CORE"])
        int(ig.instancerunningcount).should.equal(1)
        ig.instancetype.should.equal("c1.medium")
        ig.laststatechangereason.should.be.a(six.string_types)
        ig.market.should.equal("ON_DEMAND")
        ig.name.should.be.a(six.string_types)
        ig.readydatetime.should.be.a(six.string_types)
        ig.startdatetime.should.be.a(six.string_types)
        ig.state.should.equal("RUNNING")

    jf.keepjobflowalivewhennosteps.should.equal("true")
    jf.masterinstanceid.should.be.a(six.string_types)
    jf.masterinstancetype.should.equal(args["master_instance_type"])
    jf.masterpublicdnsname.should.be.a(six.string_types)
    int(jf.normalizedinstancehours).should.equal(0)
    jf.availabilityzone.should.equal(args["availability_zone"])
    jf.slaveinstancetype.should.equal(args["slave_instance_type"])
    jf.terminationprotected.should.equal("false")

    jf.jobflowid.should.equal(cluster_id)
    # jf.jobflowrole.should.equal(args['job_flow_role'])
    jf.loguri.should.equal(args["log_uri"])
    jf.name.should.equal(args["name"])
    # jf.servicerole.should.equal(args['service_role'])

    jf.steps.should.have.length_of(0)

    list(i.value for i in jf.supported_products).should.equal([])
    jf.visibletoallusers.should.equal("true")


@mock_emr_deprecated
def test_list_clusters():
    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    expected = {}

    for idx in range(40):
        cluster_name = "jobflow" + str(idx)
        args["name"] = cluster_name
        cluster_id = conn.run_jobflow(**args)
        expected[cluster_id] = {
            "id": cluster_id,
            "name": cluster_name,
            "normalizedinstancehours": "0",
            "state": "WAITING",
        }

    # need sleep since it appears the timestamp is always rounded to
    # the nearest second internally
    time.sleep(1)
    timestamp = datetime.now(pytz.utc)
    time.sleep(1)

    for idx in range(40, 70):
        cluster_name = "jobflow" + str(idx)
        args["name"] = cluster_name
        cluster_id = conn.run_jobflow(**args)
        conn.terminate_jobflow(cluster_id)
        expected[cluster_id] = {
            "id": cluster_id,
            "name": cluster_name,
            "normalizedinstancehours": "0",
            "state": "TERMINATED",
        }

    args = {}
    while 1:
        resp = conn.list_clusters(**args)
        clusters = resp.clusters
        len(clusters).should.be.lower_than_or_equal_to(50)
        for x in clusters:
            y = expected[x.id]
            x.id.should.equal(y["id"])
            x.name.should.equal(y["name"])
            x.normalizedinstancehours.should.equal(y["normalizedinstancehours"])
            x.status.state.should.equal(y["state"])
            x.status.timeline.creationdatetime.should.be.a(six.string_types)
            if y["state"] == "TERMINATED":
                x.status.timeline.enddatetime.should.be.a(six.string_types)
            else:
                x.status.timeline.shouldnt.have.property("enddatetime")
            x.status.timeline.readydatetime.should.be.a(six.string_types)
        if not hasattr(resp, "marker"):
            break
        args = {"marker": resp.marker}

    resp = conn.list_clusters(cluster_states=["TERMINATED"])
    resp.clusters.should.have.length_of(30)
    for x in resp.clusters:
        x.status.state.should.equal("TERMINATED")

    resp = conn.list_clusters(created_before=timestamp)
    resp.clusters.should.have.length_of(40)

    resp = conn.list_clusters(created_after=timestamp)
    resp.clusters.should.have.length_of(30)


@mock_emr_deprecated
def test_run_jobflow():
    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    job_id = conn.run_jobflow(**args)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.state.should.equal("WAITING")
    job_flow.jobflowid.should.equal(job_id)
    job_flow.name.should.equal(args["name"])
    job_flow.masterinstancetype.should.equal(args["master_instance_type"])
    job_flow.slaveinstancetype.should.equal(args["slave_instance_type"])
    job_flow.loguri.should.equal(args["log_uri"])
    job_flow.visibletoallusers.should.equal("false")
    int(job_flow.normalizedinstancehours).should.equal(0)
    job_flow.steps.should.have.length_of(0)


@mock_emr_deprecated
def test_run_jobflow_in_multiple_regions():
    regions = {}
    for region in ["us-east-1", "eu-west-1"]:
        conn = boto.emr.connect_to_region(region)
        args = run_jobflow_args.copy()
        args["name"] = region
        cluster_id = conn.run_jobflow(**args)
        regions[region] = {"conn": conn, "cluster_id": cluster_id}

    for region in regions.keys():
        conn = regions[region]["conn"]
        jf = conn.describe_jobflow(regions[region]["cluster_id"])
        jf.name.should.equal(region)


@requires_boto_gte("2.8")
@mock_emr_deprecated
def test_run_jobflow_with_new_params():
    # Test that run_jobflow works with newer params
    conn = boto.connect_emr()
    conn.run_jobflow(**run_jobflow_args)


@requires_boto_gte("2.8")
@mock_emr_deprecated
def test_run_jobflow_with_visible_to_all_users():
    conn = boto.connect_emr()
    for expected in (True, False):
        job_id = conn.run_jobflow(visible_to_all_users=expected, **run_jobflow_args)
        job_flow = conn.describe_jobflow(job_id)
        job_flow.visibletoallusers.should.equal(str(expected).lower())


@requires_boto_gte("2.8")
@mock_emr_deprecated
def test_run_jobflow_with_instance_groups():
    input_groups = dict((g.name, g) for g in input_instance_groups)
    conn = boto.connect_emr()
    job_id = conn.run_jobflow(instance_groups=input_instance_groups, **run_jobflow_args)
    job_flow = conn.describe_jobflow(job_id)
    int(job_flow.instancecount).should.equal(
        sum(g.num_instances for g in input_instance_groups)
    )
    for instance_group in job_flow.instancegroups:
        expected = input_groups[instance_group.name]
        instance_group.should.have.property("instancegroupid")
        int(instance_group.instancerunningcount).should.equal(expected.num_instances)
        instance_group.instancerole.should.equal(expected.role)
        instance_group.instancetype.should.equal(expected.type)
        instance_group.market.should.equal(expected.market)
        if hasattr(expected, "bidprice"):
            instance_group.bidprice.should.equal(expected.bidprice)


@requires_boto_gte("2.8")
@mock_emr_deprecated
def test_set_termination_protection():
    conn = boto.connect_emr()
    job_id = conn.run_jobflow(**run_jobflow_args)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.terminationprotected.should.equal("false")

    conn.set_termination_protection(job_id, True)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.terminationprotected.should.equal("true")

    conn.set_termination_protection(job_id, False)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.terminationprotected.should.equal("false")


@requires_boto_gte("2.8")
@mock_emr_deprecated
def test_set_visible_to_all_users():
    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    args["visible_to_all_users"] = False
    job_id = conn.run_jobflow(**args)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal("false")

    conn.set_visible_to_all_users(job_id, True)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal("true")

    conn.set_visible_to_all_users(job_id, False)
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal("false")


@mock_emr_deprecated
def test_terminate_jobflow():
    conn = boto.connect_emr()
    job_id = conn.run_jobflow(**run_jobflow_args)
    flow = conn.describe_jobflows()[0]
    flow.state.should.equal("WAITING")

    conn.terminate_jobflow(job_id)
    flow = conn.describe_jobflows()[0]
    flow.state.should.equal("TERMINATED")


# testing multiple end points for each feature


@mock_emr_deprecated
def test_bootstrap_actions():
    bootstrap_actions = [
        BootstrapAction(
            name="bs1",
            path="path/to/script",
            bootstrap_action_args=["arg1", "arg2&arg3"],
        ),
        BootstrapAction(
            name="bs2", path="path/to/anotherscript", bootstrap_action_args=[]
        ),
    ]

    conn = boto.connect_emr()
    cluster_id = conn.run_jobflow(
        bootstrap_actions=bootstrap_actions, **run_jobflow_args
    )

    jf = conn.describe_jobflow(cluster_id)
    for x, y in zip(jf.bootstrapactions, bootstrap_actions):
        x.name.should.equal(y.name)
        x.path.should.equal(y.path)
        list(o.value for o in x.args).should.equal(y.args())

    resp = conn.list_bootstrap_actions(cluster_id)
    for i, y in enumerate(bootstrap_actions):
        x = resp.actions[i]
        x.name.should.equal(y.name)
        x.scriptpath.should.equal(y.path)
        list(arg.value for arg in x.args).should.equal(y.args())


@mock_emr_deprecated
def test_instance_groups():
    input_groups = dict((g.name, g) for g in input_instance_groups)

    conn = boto.connect_emr()
    args = run_jobflow_args.copy()
    for key in ["master_instance_type", "slave_instance_type", "num_instances"]:
        del args[key]
    args["instance_groups"] = input_instance_groups[:2]
    job_id = conn.run_jobflow(**args)

    jf = conn.describe_jobflow(job_id)
    base_instance_count = int(jf.instancecount)

    conn.add_instance_groups(job_id, input_instance_groups[2:])

    jf = conn.describe_jobflow(job_id)
    int(jf.instancecount).should.equal(
        sum(g.num_instances for g in input_instance_groups)
    )
    for x in jf.instancegroups:
        y = input_groups[x.name]
        if hasattr(y, "bidprice"):
            x.bidprice.should.equal(y.bidprice)
        x.creationdatetime.should.be.a(six.string_types)
        # x.enddatetime.should.be.a(six.string_types)
        x.should.have.property("instancegroupid")
        int(x.instancerequestcount).should.equal(y.num_instances)
        x.instancerole.should.equal(y.role)
        int(x.instancerunningcount).should.equal(y.num_instances)
        x.instancetype.should.equal(y.type)
        x.laststatechangereason.should.be.a(six.string_types)
        x.market.should.equal(y.market)
        x.name.should.be.a(six.string_types)
        x.readydatetime.should.be.a(six.string_types)
        x.startdatetime.should.be.a(six.string_types)
        x.state.should.equal("RUNNING")

    for x in conn.list_instance_groups(job_id).instancegroups:
        y = input_groups[x.name]
        if hasattr(y, "bidprice"):
            x.bidprice.should.equal(y.bidprice)
        # Configurations
        # EbsBlockDevices
        # EbsOptimized
        x.should.have.property("id")
        x.instancegrouptype.should.equal(y.role)
        x.instancetype.should.equal(y.type)
        x.market.should.equal(y.market)
        x.name.should.equal(y.name)
        int(x.requestedinstancecount).should.equal(y.num_instances)
        int(x.runninginstancecount).should.equal(y.num_instances)
        # ShrinkPolicy
        x.status.state.should.equal("RUNNING")
        x.status.statechangereason.code.should.be.a(six.string_types)
        x.status.statechangereason.message.should.be.a(six.string_types)
        x.status.timeline.creationdatetime.should.be.a(six.string_types)
        # x.status.timeline.enddatetime.should.be.a(six.string_types)
        x.status.timeline.readydatetime.should.be.a(six.string_types)

    igs = dict((g.name, g) for g in jf.instancegroups)

    conn.modify_instance_groups(
        [igs["task-1"].instancegroupid, igs["task-2"].instancegroupid], [2, 3]
    )
    jf = conn.describe_jobflow(job_id)
    int(jf.instancecount).should.equal(base_instance_count + 5)
    igs = dict((g.name, g) for g in jf.instancegroups)
    int(igs["task-1"].instancerunningcount).should.equal(2)
    int(igs["task-2"].instancerunningcount).should.equal(3)


@mock_emr_deprecated
def test_steps():
    input_steps = [
        StreamingStep(
            name="My wordcount example",
            mapper="s3n://elasticmapreduce/samples/wordcount/wordSplitter.py",
            reducer="aggregate",
            input="s3n://elasticmapreduce/samples/wordcount/input",
            output="s3n://output_bucket/output/wordcount_output",
        ),
        StreamingStep(
            name="My wordcount example & co.",
            mapper="s3n://elasticmapreduce/samples/wordcount/wordSplitter2.py",
            reducer="aggregate",
            input="s3n://elasticmapreduce/samples/wordcount/input2",
            output="s3n://output_bucket/output/wordcount_output2",
        ),
    ]

    # TODO: implementation and test for cancel_steps

    conn = boto.connect_emr()
    cluster_id = conn.run_jobflow(steps=[input_steps[0]], **run_jobflow_args)

    jf = conn.describe_jobflow(cluster_id)
    jf.steps.should.have.length_of(1)

    conn.add_jobflow_steps(cluster_id, [input_steps[1]])

    jf = conn.describe_jobflow(cluster_id)
    jf.steps.should.have.length_of(2)
    for step in jf.steps:
        step.actiononfailure.should.equal("TERMINATE_JOB_FLOW")
        list(arg.value for arg in step.args).should.have.length_of(8)
        step.creationdatetime.should.be.a(six.string_types)
        # step.enddatetime.should.be.a(six.string_types)
        step.jar.should.equal("/home/hadoop/contrib/streaming/hadoop-streaming.jar")
        step.laststatechangereason.should.be.a(six.string_types)
        step.mainclass.should.equal("")
        step.name.should.be.a(six.string_types)
        # step.readydatetime.should.be.a(six.string_types)
        # step.startdatetime.should.be.a(six.string_types)
        step.state.should.be.within(["STARTING", "PENDING"])

    expected = dict((s.name, s) for s in input_steps)

    steps = conn.list_steps(cluster_id).steps
    for x in steps:
        y = expected[x.name]
        # actiononfailure
        list(arg.value for arg in x.config.args).should.equal(
            [
                "-mapper",
                y.mapper,
                "-reducer",
                y.reducer,
                "-input",
                y.input,
                "-output",
                y.output,
            ]
        )
        x.config.jar.should.equal("/home/hadoop/contrib/streaming/hadoop-streaming.jar")
        x.config.mainclass.should.equal("")
        # properties
        x.should.have.property("id").should.be.a(six.string_types)
        x.name.should.equal(y.name)
        x.status.state.should.be.within(["STARTING", "PENDING"])
        # x.status.statechangereason
        x.status.timeline.creationdatetime.should.be.a(six.string_types)
        # x.status.timeline.enddatetime.should.be.a(six.string_types)
        # x.status.timeline.startdatetime.should.be.a(six.string_types)

        x = conn.describe_step(cluster_id, x.id)
        list(arg.value for arg in x.config.args).should.equal(
            [
                "-mapper",
                y.mapper,
                "-reducer",
                y.reducer,
                "-input",
                y.input,
                "-output",
                y.output,
            ]
        )
        x.config.jar.should.equal("/home/hadoop/contrib/streaming/hadoop-streaming.jar")
        x.config.mainclass.should.equal("")
        # properties
        x.should.have.property("id").should.be.a(six.string_types)
        x.name.should.equal(y.name)
        x.status.state.should.be.within(["STARTING", "PENDING"])
        # x.status.statechangereason
        x.status.timeline.creationdatetime.should.be.a(six.string_types)
        # x.status.timeline.enddatetime.should.be.a(six.string_types)
        # x.status.timeline.startdatetime.should.be.a(six.string_types)

    @requires_boto_gte("2.39")
    def test_list_steps_with_states():
        # boto's list_steps prior to 2.39 has a bug that ignores
        # step_states argument.
        steps = conn.list_steps(cluster_id).steps
        step_id = steps[0].id
        steps = conn.list_steps(cluster_id, step_states=["STARTING"]).steps
        steps.should.have.length_of(1)
        steps[0].id.should.equal(step_id)

    test_list_steps_with_states()


@mock_emr_deprecated
def test_tags():
    input_tags = {"tag1": "val1", "tag2": "val2"}

    conn = boto.connect_emr()
    cluster_id = conn.run_jobflow(**run_jobflow_args)

    conn.add_tags(cluster_id, input_tags)
    cluster = conn.describe_cluster(cluster_id)
    cluster.tags.should.have.length_of(2)
    dict((t.key, t.value) for t in cluster.tags).should.equal(input_tags)

    conn.remove_tags(cluster_id, list(input_tags.keys()))
    cluster = conn.describe_cluster(cluster_id)
    cluster.tags.should.have.length_of(0)
