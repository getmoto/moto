# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_emr


@mock_emr
def test_run_job_flow():
    client = boto3.client('emr', region_name='us-east-1')
    cluster_id = client.run_job_flow(
        Name='cluster',
        Instances={
            'MasterInstanceType': 'c3.xlarge',
            'SlaveInstanceType': 'c3.xlarge',
            'InstanceCount': 3,
            'Placement': {'AvailabilityZone': 'us-east-1a'},
            'KeepJobFlowAliveWhenNoSteps': True,
        },
        VisibleToAllUsers=True,
    )
    cluster_id.should.have.key('JobFlowId')


@mock_emr
def test_list_clusters():
    client = boto3.client('emr', region_name='us-east-1')
    client.run_job_flow(
        Name='cluster',
        Instances={
            'MasterInstanceType': 'c3.xlarge',
            'SlaveInstanceType': 'c3.xlarge',
            'InstanceCount': 3,
            'Placement': {'AvailabilityZone': 'us-east-1a'},
            'KeepJobFlowAliveWhenNoSteps': True,
        },
        VisibleToAllUsers=True,
    )
    summary = client.list_clusters()
    clusters = summary['Clusters']
    clusters.should.have.length_of(1)
    cluster = clusters[0]
    cluster['NormalizedInstanceHours'].should.equal(0)
    cluster['Status']['State'].should.equal("RUNNING")


@mock_emr
def test_describe_cluster():
    client = boto3.client('emr', region_name='us-east-1')
    resp = client.run_job_flow(
        Name='cluster',
        LogUri='s3://mybucket/log',
        Instances={
            'MasterInstanceType': 'c3.xlarge',
            'SlaveInstanceType': 'c3.xlarge',
            'InstanceCount': 3,
            'Placement': {'AvailabilityZone': 'us-east-1a'},
            'KeepJobFlowAliveWhenNoSteps': True,
        },
        VisibleToAllUsers=True,
    )
    cluster_id = resp['JobFlowId']

    resp = client.describe_cluster(ClusterId=cluster_id)

    cluster = resp['Cluster']
    cluster['Id'].should.equal(cluster_id)
    cluster['Name'].should.equal('cluster')
    cluster['LogUri'].should.equal('s3://mybucket/log')
    cluster['NormalizedInstanceHours'].should.equal(0)
    cluster['Status']['State'].should.equal('RUNNING')


@mock_emr
def test_terminate_job_flows():
    client = boto3.client('emr', region_name='us-east-1')
    resp = client.run_job_flow(
        Name='cluster',
        LogUri='s3://mybucket/log',
        Instances={
            'MasterInstanceType': 'c3.xlarge',
            'SlaveInstanceType': 'c3.xlarge',
            'InstanceCount': 3,
            'Placement': {'AvailabilityZone': 'us-east-1a'},
            'KeepJobFlowAliveWhenNoSteps': True,
        },
        VisibleToAllUsers=True,
    )
    cluster_id = resp['JobFlowId']

    client.terminate_job_flows(JobFlowIds=[cluster_id])

    resp = client.describe_job_flows(JobFlowIds=[cluster_id])
    resp['JobFlows'].should.have.length_of(1)
    jobflow = resp['JobFlows'][0]
    jobflow['ExecutionStatusDetail']['State'].should.equal('TERMINATED')
