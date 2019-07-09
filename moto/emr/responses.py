from __future__ import unicode_literals
import json
import re
from datetime import datetime
from functools import wraps

import pytz

from six.moves.urllib.parse import urlparse
from moto.core.responses import AWSServiceSpec
from moto.core.responses import BaseResponse
from moto.core.responses import xml_to_json_response
from .exceptions import EmrError
from .models import emr_backends
from .utils import steps_from_query_string, tags_from_query_string


def generate_boto3_response(operation):
    """The decorator to convert an XML response to JSON, if the request is
    determined to be from boto3. Pass the API action as a parameter.

    """
    def _boto3_request(method):
        @wraps(method)
        def f(self, *args, **kwargs):
            rendered = method(self, *args, **kwargs)
            if 'json' in self.headers.get('Content-Type', []):
                self.response_headers.update(
                    {'x-amzn-requestid': '2690d7eb-ed86-11dd-9877-6fad448a8419',
                     'date': datetime.now(pytz.utc).strftime('%a, %d %b %Y %H:%M:%S %Z'),
                     'content-type': 'application/x-amz-json-1.1'})
                resp = xml_to_json_response(
                    self.aws_service_spec, operation, rendered)
                return '' if resp is None else json.dumps(resp)
            return rendered
        return f
    return _boto3_request


class ElasticMapReduceResponse(BaseResponse):

    # EMR end points are inconsistent in the placement of region name
    # in the URL, so parsing it out needs to be handled differently
    region_regex = [re.compile(r'elasticmapreduce\.(.+?)\.amazonaws\.com'),
                    re.compile(r'(.+?)\.elasticmapreduce\.amazonaws\.com')]

    aws_service_spec = AWSServiceSpec('data/emr/2009-03-31/service-2.json')

    def get_region_from_url(self, request, full_url):
        parsed = urlparse(full_url)
        for regex in self.region_regex:
            match = regex.search(parsed.netloc)
            if match:
                return match.group(1)
        return self.default_region

    @property
    def backend(self):
        return emr_backends[self.region]

    @generate_boto3_response('AddInstanceGroups')
    def add_instance_groups(self):
        jobflow_id = self._get_param('JobFlowId')
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        for item in instance_groups:
            item['instance_count'] = int(item['instance_count'])
        instance_groups = self.backend.add_instance_groups(
            jobflow_id, instance_groups)
        template = self.response_template(ADD_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    @generate_boto3_response('AddJobFlowSteps')
    def add_job_flow_steps(self):
        job_flow_id = self._get_param('JobFlowId')
        steps = self.backend.add_job_flow_steps(
            job_flow_id, steps_from_query_string(self._get_list_prefix('Steps.member')))
        template = self.response_template(ADD_JOB_FLOW_STEPS_TEMPLATE)
        return template.render(steps=steps)

    @generate_boto3_response('AddTags')
    def add_tags(self):
        cluster_id = self._get_param('ResourceId')
        tags = tags_from_query_string(self.querystring)
        self.backend.add_tags(cluster_id, tags)
        template = self.response_template(ADD_TAGS_TEMPLATE)
        return template.render()

    def cancel_steps(self):
        raise NotImplementedError

    def create_security_configuration(self):
        raise NotImplementedError

    def delete_security_configuration(self):
        raise NotImplementedError

    @generate_boto3_response('DescribeCluster')
    def describe_cluster(self):
        cluster_id = self._get_param('ClusterId')
        cluster = self.backend.get_cluster(cluster_id)
        template = self.response_template(DESCRIBE_CLUSTER_TEMPLATE)
        return template.render(cluster=cluster)

    @generate_boto3_response('DescribeJobFlows')
    def describe_job_flows(self):
        created_after = self._get_param('CreatedAfter')
        created_before = self._get_param('CreatedBefore')
        job_flow_ids = self._get_multi_param("JobFlowIds.member")
        job_flow_states = self._get_multi_param('JobFlowStates.member')
        clusters = self.backend.describe_job_flows(
            job_flow_ids, job_flow_states, created_after, created_before)
        template = self.response_template(DESCRIBE_JOB_FLOWS_TEMPLATE)
        return template.render(clusters=clusters)

    def describe_security_configuration(self):
        raise NotImplementedError

    @generate_boto3_response('DescribeStep')
    def describe_step(self):
        cluster_id = self._get_param('ClusterId')
        step_id = self._get_param('StepId')
        step = self.backend.describe_step(cluster_id, step_id)
        template = self.response_template(DESCRIBE_STEP_TEMPLATE)
        return template.render(step=step)

    @generate_boto3_response('ListBootstrapActions')
    def list_bootstrap_actions(self):
        cluster_id = self._get_param('ClusterId')
        marker = self._get_param('Marker')
        bootstrap_actions, marker = self.backend.list_bootstrap_actions(
            cluster_id, marker)
        template = self.response_template(LIST_BOOTSTRAP_ACTIONS_TEMPLATE)
        return template.render(bootstrap_actions=bootstrap_actions, marker=marker)

    @generate_boto3_response('ListClusters')
    def list_clusters(self):
        cluster_states = self._get_multi_param('ClusterStates.member')
        created_after = self._get_param('CreatedAfter')
        created_before = self._get_param('CreatedBefore')
        marker = self._get_param('Marker')
        clusters, marker = self.backend.list_clusters(
            cluster_states, created_after, created_before, marker)
        template = self.response_template(LIST_CLUSTERS_TEMPLATE)
        return template.render(clusters=clusters, marker=marker)

    @generate_boto3_response('ListInstanceGroups')
    def list_instance_groups(self):
        cluster_id = self._get_param('ClusterId')
        marker = self._get_param('Marker')
        instance_groups, marker = self.backend.list_instance_groups(
            cluster_id, marker=marker)
        template = self.response_template(LIST_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups, marker=marker)

    def list_instances(self):
        raise NotImplementedError

    @generate_boto3_response('ListSteps')
    def list_steps(self):
        cluster_id = self._get_param('ClusterId')
        marker = self._get_param('Marker')
        step_ids = self._get_multi_param('StepIds.member')
        step_states = self._get_multi_param('StepStates.member')
        steps, marker = self.backend.list_steps(
            cluster_id, marker=marker, step_ids=step_ids, step_states=step_states)
        template = self.response_template(LIST_STEPS_TEMPLATE)
        return template.render(steps=steps, marker=marker)

    @generate_boto3_response('ModifyInstanceGroups')
    def modify_instance_groups(self):
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        for item in instance_groups:
            item['instance_count'] = int(item['instance_count'])
        instance_groups = self.backend.modify_instance_groups(instance_groups)
        template = self.response_template(MODIFY_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    @generate_boto3_response('RemoveTags')
    def remove_tags(self):
        cluster_id = self._get_param('ResourceId')
        tag_keys = self._get_multi_param('TagKeys.member')
        self.backend.remove_tags(cluster_id, tag_keys)
        template = self.response_template(REMOVE_TAGS_TEMPLATE)
        return template.render()

    @generate_boto3_response('RunJobFlow')
    def run_job_flow(self):
        instance_attrs = dict(
            master_instance_type=self._get_param(
                'Instances.MasterInstanceType'),
            slave_instance_type=self._get_param('Instances.SlaveInstanceType'),
            instance_count=self._get_int_param('Instances.InstanceCount', 1),
            ec2_key_name=self._get_param('Instances.Ec2KeyName'),
            ec2_subnet_id=self._get_param('Instances.Ec2SubnetId'),
            hadoop_version=self._get_param('Instances.HadoopVersion'),
            availability_zone=self._get_param(
                'Instances.Placement.AvailabilityZone', self.backend.region_name + 'a'),
            keep_job_flow_alive_when_no_steps=self._get_bool_param(
                'Instances.KeepJobFlowAliveWhenNoSteps', False),
            termination_protected=self._get_bool_param(
                'Instances.TerminationProtected', False),
            emr_managed_master_security_group=self._get_param(
                'Instances.EmrManagedMasterSecurityGroup'),
            emr_managed_slave_security_group=self._get_param(
                'Instances.EmrManagedSlaveSecurityGroup'),
            service_access_security_group=self._get_param(
                'Instances.ServiceAccessSecurityGroup'),
            additional_master_security_groups=self._get_multi_param(
                'Instances.AdditionalMasterSecurityGroups.member.'),
            additional_slave_security_groups=self._get_multi_param('Instances.AdditionalSlaveSecurityGroups.member.'))

        kwargs = dict(
            name=self._get_param('Name'),
            log_uri=self._get_param('LogUri'),
            job_flow_role=self._get_param('JobFlowRole'),
            service_role=self._get_param('ServiceRole'),
            steps=steps_from_query_string(
                self._get_list_prefix('Steps.member')),
            visible_to_all_users=self._get_bool_param(
                'VisibleToAllUsers', False),
            instance_attrs=instance_attrs,
        )

        bootstrap_actions = self._get_list_prefix('BootstrapActions.member')
        if bootstrap_actions:
            for ba in bootstrap_actions:
                args = []
                idx = 1
                keyfmt = 'script_bootstrap_action._args.member.{0}'
                key = keyfmt.format(idx)
                while key in ba:
                    args.append(ba.pop(key))
                    idx += 1
                    key = keyfmt.format(idx)
                ba['args'] = args
                ba['script_path'] = ba.pop('script_bootstrap_action._path')
            kwargs['bootstrap_actions'] = bootstrap_actions

        configurations = self._get_list_prefix('Configurations.member')
        if configurations:
            for idx, config in enumerate(configurations, 1):
                for key in list(config.keys()):
                    if key.startswith('properties.'):
                        config.pop(key)
                config['properties'] = {}
                map_items = self._get_map_prefix(
                    'Configurations.member.{0}.Properties.entry'.format(idx))
                config['properties'] = map_items

            kwargs['configurations'] = configurations

        release_label = self._get_param('ReleaseLabel')
        ami_version = self._get_param('AmiVersion')
        if release_label:
            kwargs['release_label'] = release_label
            if ami_version:
                message = (
                    'Only one AMI version and release label may be specified. '
                    'Provided AMI: {0}, release label: {1}.').format(
                        ami_version, release_label)
                raise EmrError(error_type="ValidationException",
                               message=message, template='error_json')
        else:
            if ami_version:
                kwargs['requested_ami_version'] = ami_version
                kwargs['running_ami_version'] = ami_version
            else:
                kwargs['running_ami_version'] = '1.0.0'

        custom_ami_id = self._get_param('CustomAmiId')
        if custom_ami_id:
            kwargs['custom_ami_id'] = custom_ami_id
            if release_label and release_label < 'emr-5.7.0':
                message = 'Custom AMI is not allowed'
                raise EmrError(error_type='ValidationException',
                            message=message, template='error_json')
            elif ami_version:
                message = 'Custom AMI is not supported in this version of EMR'
                raise EmrError(error_type='ValidationException',
                            message=message, template='error_json')

        cluster = self.backend.run_job_flow(**kwargs)

        applications = self._get_list_prefix('Applications.member')
        if applications:
            self.backend.add_applications(cluster.id, applications)
        else:
            self.backend.add_applications(
                cluster.id, [{'Name': 'Hadoop', 'Version': '0.18'}])

        instance_groups = self._get_list_prefix(
            'Instances.InstanceGroups.member')
        if instance_groups:
            for ig in instance_groups:
                ig['instance_count'] = int(ig['instance_count'])
            self.backend.add_instance_groups(cluster.id, instance_groups)

        tags = self._get_list_prefix('Tags.member')
        if tags:
            self.backend.add_tags(
                cluster.id, dict((d['key'], d['value']) for d in tags))

        template = self.response_template(RUN_JOB_FLOW_TEMPLATE)
        return template.render(cluster=cluster)

    @generate_boto3_response('SetTerminationProtection')
    def set_termination_protection(self):
        termination_protection = self._get_param('TerminationProtected')
        job_ids = self._get_multi_param('JobFlowIds.member')
        self.backend.set_termination_protection(
            job_ids, termination_protection)
        template = self.response_template(SET_TERMINATION_PROTECTION_TEMPLATE)
        return template.render()

    @generate_boto3_response('SetVisibleToAllUsers')
    def set_visible_to_all_users(self):
        visible_to_all_users = self._get_param('VisibleToAllUsers')
        job_ids = self._get_multi_param('JobFlowIds.member')
        self.backend.set_visible_to_all_users(job_ids, visible_to_all_users)
        template = self.response_template(SET_VISIBLE_TO_ALL_USERS_TEMPLATE)
        return template.render()

    @generate_boto3_response('TerminateJobFlows')
    def terminate_job_flows(self):
        job_ids = self._get_multi_param('JobFlowIds.member.')
        self.backend.terminate_job_flows(job_ids)
        template = self.response_template(TERMINATE_JOB_FLOWS_TEMPLATE)
        return template.render()


ADD_INSTANCE_GROUPS_TEMPLATE = """<AddInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <AddInstanceGroupsResult>
    <InstanceGroupIds>
      {% for instance_group in instance_groups %}
      <member>{{ instance_group.id }}</member>
      {% endfor %}
    </InstanceGroupIds>
  </AddInstanceGroupsResult>
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</AddInstanceGroupsResponse>"""

ADD_JOB_FLOW_STEPS_TEMPLATE = """<AddJobFlowStepsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <AddJobFlowStepsResult>
    <StepIds>
      {% for step in steps %}
      <member>{{ step.id }}</member>
      {% endfor %}
    </StepIds>
  </AddJobFlowStepsResult>
  <ResponseMetadata>
    <RequestId>df6f4f4a-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</AddJobFlowStepsResponse>"""

ADD_TAGS_TEMPLATE = """<AddTagsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</AddTagsResponse>"""

DESCRIBE_CLUSTER_TEMPLATE = """<DescribeClusterResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <DescribeClusterResult>
    <Cluster>
      <Applications>
        {% for application in cluster.applications %}
        <member>
          <Name>{{ application.name }}</Name>
          <Version>{{ application.version }}</Version>
        </member>
        {% endfor %}
      </Applications>
      <AutoTerminate>{{ (not cluster.keep_job_flow_alive_when_no_steps)|lower }}</AutoTerminate>
      <Configurations>
        {% for configuration in cluster.configurations %}
        <member>
          <Classification>{{ configuration['classification'] }}</Classification>
          <Properties>
            {% for key, value in configuration['properties'].items() %}
            <entry>
              <key>{{ key }}</key>
              <value>{{ value }}</value>
            </entry>
            {% endfor %}
          </Properties>
        </member>
        {% endfor %}
      </Configurations>
      {% if cluster.custom_ami_id is not none %}
      <CustomAmiId>{{ cluster.custom_ami_id }}</CustomAmiId>
      {% endif %}
      <Ec2InstanceAttributes>
        <AdditionalMasterSecurityGroups>
        {% for each in cluster.additional_master_security_groups %}
          <member>{{ each }}</member>
        {% endfor %}
        </AdditionalMasterSecurityGroups>
        <AdditionalSlaveSecurityGroups>
        {% for each in cluster.additional_slave_security_groups %}
          <member>{{ each }}</member>
        {% endfor %}
        </AdditionalSlaveSecurityGroups>
        <Ec2AvailabilityZone>{{ cluster.availability_zone }}</Ec2AvailabilityZone>
        <Ec2KeyName>{{ cluster.ec2_key_name }}</Ec2KeyName>
        <Ec2SubnetId>{{ cluster.ec2_subnet_id }}</Ec2SubnetId>
        <IamInstanceProfile>{{ cluster.role }}</IamInstanceProfile>
        <EmrManagedMasterSecurityGroup>{{ cluster.master_security_group }}</EmrManagedMasterSecurityGroup>
        <EmrManagedSlaveSecurityGroup>{{ cluster.slave_security_group }}</EmrManagedSlaveSecurityGroup>
        <ServiceAccessSecurityGroup>{{ cluster.service_access_security_group }}</ServiceAccessSecurityGroup>
      </Ec2InstanceAttributes>
      <Id>{{ cluster.id }}</Id>
      <LogUri>{{ cluster.log_uri }}</LogUri>
      <MasterPublicDnsName>ec2-184-0-0-1.us-west-1.compute.amazonaws.com</MasterPublicDnsName>
      <Name>{{ cluster.name }}</Name>
      <NormalizedInstanceHours>{{ cluster.normalized_instance_hours }}</NormalizedInstanceHours>
      {% if cluster.release_label is not none %}
      <ReleaseLabel>{{ cluster.release_label }}</ReleaseLabel>
      {% endif %}
      {% if cluster.requested_ami_version is not none %}
      <RequestedAmiVersion>{{ cluster.requested_ami_version }}</RequestedAmiVersion>
      {% endif %}
      {% if cluster.running_ami_version is not none %}
      <RunningAmiVersion>{{ cluster.running_ami_version }}</RunningAmiVersion>
      {% endif %}
      <SecurityConfiguration/>
      <ServiceRole>{{ cluster.service_role }}</ServiceRole>
      <Status>
        <State>{{ cluster.state }}</State>
        <StateChangeReason>
          {% if cluster.last_state_change_reason is not none %}
          <Message>{{ cluster.last_state_change_reason }}</Message>
          {% endif %}
          <Code>USER_REQUEST</Code>
        </StateChangeReason>
        <Timeline>
          <CreationDateTime>{{ cluster.creation_datetime.isoformat() }}</CreationDateTime>
          {% if cluster.end_datetime is not none %}
          <EndDateTime>{{ cluster.end_datetime.isoformat() }}</EndDateTime>
          {% endif %}
          {% if cluster.ready_datetime is not none %}
          <ReadyDateTime>{{ cluster.ready_datetime.isoformat() }}</ReadyDateTime>
          {% endif %}
        </Timeline>
      </Status>
      <Tags>
        {% for tag_key, tag_value in cluster.tags.items() %}
        <member>
          <Key>{{ tag_key }}</Key>
          <Value>{{ tag_value }}</Value>
        </member>
        {% endfor %}
      </Tags>
      <TerminationProtected>{{ cluster.termination_protected|lower }}</TerminationProtected>
      <VisibleToAllUsers>{{ cluster.visible_to_all_users|lower }}</VisibleToAllUsers>
    </Cluster>
  </DescribeClusterResult>
  <ResponseMetadata>
    <RequestId>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</RequestId>
  </ResponseMetadata>
</DescribeClusterResponse>"""

DESCRIBE_JOB_FLOWS_TEMPLATE = """<DescribeJobFlowsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <DescribeJobFlowsResult>
    <JobFlows>
      {% for cluster in clusters %}
      <member>
        {% if cluster.running_ami_version is not none %}
        <AmiVersion>{{ cluster.running_ami_version }}</AmiVersion>
        {% endif %}
        {% if cluster.bootstrap_actions %}
        <BootstrapActions>
          {% for bootstrap_action in cluster.bootstrap_actions %}
          <member>
            <BootstrapActionConfig>
              <Name>{{ bootstrap_action.name }}</Name>
              <ScriptBootstrapAction>
                <Args>
                  {% for arg in bootstrap_action.args %}
                  <member>{{ arg | escape }}</member>
                  {% endfor %}
                </Args>
                <Path>{{ bootstrap_action.script_path | escape }}</Path>
              </ScriptBootstrapAction>
            </BootstrapActionConfig>
          </member>
          {% endfor %}
        </BootstrapActions>
        {% endif %}
        <ExecutionStatusDetail>
          <CreationDateTime>{{ cluster.creation_datetime.isoformat() }}</CreationDateTime>
          {% if cluster.end_datetime is not none %}
          <EndDateTime>{{ cluster.end_datetime.isoformat() }}</EndDateTime>
          {% endif %}
          {% if cluster.last_state_change_reason is not none %}
          <LastStateChangeReason>{{ cluster.last_state_change_reason }}</LastStateChangeReason>
          {% endif %}
          {% if cluster.ready_datetime is not none %}
          <ReadyDateTime>{{ cluster.ready_datetime.isoformat() }}</ReadyDateTime>
          {% endif %}
          {% if cluster.start_datetime is not none %}
          <StartDateTime>{{ cluster.start_datetime.isoformat() }}</StartDateTime>
          {% endif %}
          <State>{{ cluster.state }}</State>
        </ExecutionStatusDetail>
        <Instances>
          {% if cluster.ec2_key_name is not none %}
          <Ec2KeyName>{{ cluster.ec2_key_name }}</Ec2KeyName>
          {% endif %}
          {% if cluster.ec2_subnet_id is not none %}
          <Ec2SubnetId>{{ cluster.ec2_subnet_id }}</Ec2SubnetId>
          {% endif %}
          <HadoopVersion>{{ cluster.hadoop_version }}</HadoopVersion>
          <InstanceCount>{{ cluster.instance_count }}</InstanceCount>
          <InstanceGroups>
            {% for instance_group in cluster.instance_groups %}
            <member>
              {% if instance_group.bid_price is not none %}
              <BidPrice>{{ instance_group.bid_price }}</BidPrice>
              {% endif %}
              <CreationDateTime>{{ instance_group.creation_datetime.isoformat() }}</CreationDateTime>
              {% if instance_group.end_datetime is not none %}
              <EndDateTime>{{ instance_group.end_datetime.isoformat() }}</EndDateTime>
              {% endif %}

              <InstanceGroupId>{{ instance_group.id }}</InstanceGroupId>
              <InstanceRequestCount>{{ instance_group.num_instances }}</InstanceRequestCount>
              <InstanceRole>{{ instance_group.role }}</InstanceRole>
              <InstanceRunningCount>{{ instance_group.num_instances }}</InstanceRunningCount>
              <InstanceType>{{ instance_group.type }}</InstanceType>
              <LastStateChangeReason/>
              <Market>{{ instance_group.market }}</Market>
              <Name>{{ instance_group.name }}</Name>
              {% if instance_group.ready_datetime is not none %}
              <ReadyDateTime>{{ instance_group.ready_datetime.isoformat() }}</ReadyDateTime>
              {% endif %}
              {% if instance_group.start_datetime is not none %}
              <StartDateTime>{{ instance_group.start_datetime.isoformat() }}</StartDateTime>
              {% endif %}
              <State>{{ instance_group.state }}</State>
            </member>
            {% endfor %}
          </InstanceGroups>
          <KeepJobFlowAliveWhenNoSteps>{{ cluster.keep_job_flow_alive_when_no_steps|lower }}</KeepJobFlowAliveWhenNoSteps>
          <MasterInstanceId>{{ cluster.master_instance_id }}</MasterInstanceId>
          <MasterInstanceType>{{ cluster.master_instance_type }}</MasterInstanceType>
          <MasterPublicDnsName>ec2-184-0-0-1.{{ cluster.region }}.compute.amazonaws.com</MasterPublicDnsName>
          <NormalizedInstanceHours>{{ cluster.normalized_instance_hours }}</NormalizedInstanceHours>
          <Placement>
            <AvailabilityZone>{{ cluster.availability_zone }}</AvailabilityZone>
          </Placement>
          <SlaveInstanceType>{{ cluster.slave_instance_type }}</SlaveInstanceType>
          <TerminationProtected>{{ cluster.termination_protected|lower }}</TerminationProtected>
        </Instances>
        <JobFlowId>{{ cluster.id }}</JobFlowId>
        <JobFlowRole>{{ cluster.role }}</JobFlowRole>
        <LogUri>{{ cluster.log_uri }}</LogUri>
        <Name>{{ cluster.name }}</Name>
        <ServiceRole>{{ cluster.service_role }}</ServiceRole>
        <Steps>
          {% for step in cluster.steps %}
          <member>
            <ExecutionStatusDetail>
              <CreationDateTime>{{ step.creation_datetime.isoformat() }}</CreationDateTime>
              {% if step.end_datetime is not none %}
              <EndDateTime>{{ step.end_datetime.isoformat() }}</EndDateTime>
              {% endif %}
              {% if step.last_state_change_reason is not none %}
              <LastStateChangeReason>{{ step.last_state_change_reason }}</LastStateChangeReason>
              {% endif %}
              {% if step.ready_datetime is not none %}
              <ReadyDateTime>{{ step.ready_datetime.isoformat() }}</ReadyDateTime>
              {% endif %}
              {% if step.start_datetime is not none %}
              <StartDateTime>{{ step.start_datetime.isoformat() }}</StartDateTime>
              {% endif %}
              <State>{{ step.state }}</State>
            </ExecutionStatusDetail>
            <StepConfig>
              <ActionOnFailure>{{ step.action_on_failure }}</ActionOnFailure>
              <HadoopJarStep>
                <Jar>{{ step.jar }}</Jar>
                <MainClass>{{ step.main_class }}</MainClass>
                <Args>
                  {% for arg in step.args %}
                  <member>{{ arg | escape }}</member>
                  {% endfor %}
                </Args>
                <Properties/>
              </HadoopJarStep>
              <Name>{{ step.name | escape }}</Name>
            </StepConfig>
          </member>
          {% endfor %}
        </Steps>
        <SupportedProducts/>
        <VisibleToAllUsers>{{ cluster.visible_to_all_users|lower }}</VisibleToAllUsers>
      </member>
      {% endfor %}
    </JobFlows>
  </DescribeJobFlowsResult>
  <ResponseMetadata>
    <RequestId>9cea3229-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</DescribeJobFlowsResponse>"""

DESCRIBE_STEP_TEMPLATE = """<DescribeStepResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <DescribeStepResult>
    <Step>
      <ActionOnFailure>{{ step.action_on_failure }}</ActionOnFailure>
      <Config>
        <Args>
          {% for arg in step.args %}
          <member>{{ arg | escape }}</member>
          {% endfor %}
        </Args>
        <Jar>{{ step.jar }}</Jar>
        <MainClass/>
        <Properties>
          {% for key, val in step.properties.items() %}
          <member>
            <key>{{ key }}</key>
            <value>{{ val | escape }}</value>
          </member>
          {% endfor %}
        </Properties>
      </Config>
      <Id>{{ step.id }}</Id>
      <Name>{{ step.name | escape }}</Name>
      <Status>
        <FailureDetails>
          <Reason/>
          <Message/>
          <LogFile/>
        </FailureDetails>
        <State>{{ step.state }}</State>
        <StateChangeReason>{{ step.state_change_reason }}</StateChangeReason>
        <Timeline>
          <CreationDateTime>{{ step.creation_datetime.isoformat() }}</CreationDateTime>
          {% if step.end_datetime is not none %}
          <EndDateTime>{{ step.end_datetime.isoformat() }}</EndDateTime>
          {% endif %}
          {% if step.ready_datetime is not none %}
          <StartDateTime>{{ step.start_datetime.isoformat() }}</StartDateTime>
          {% endif %}
        </Timeline>
      </Status>
    </Step>
  </DescribeStepResult>
  <ResponseMetadata>
    <RequestId>df6f4f4a-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</DescribeStepResponse>"""

LIST_BOOTSTRAP_ACTIONS_TEMPLATE = """<ListBootstrapActionsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ListBootstrapActionsResult>
    <BootstrapActions>
      {% for bootstrap_action in bootstrap_actions %}
      <member>
        <Args>
          {% for arg in bootstrap_action.args %}
          <member>{{ arg | escape }}</member>
          {% endfor %}
        </Args>
        <Name>{{ bootstrap_action.name }}</Name>
        <ScriptPath>{{ bootstrap_action.script_path }}</ScriptPath>
      </member>
      {% endfor %}
    </BootstrapActions>
    {% if marker is not none %}
    <Marker>{{ marker }}</Marker>
    {% endif %}
  </ListBootstrapActionsResult>
  <ResponseMetadata>
    <RequestId>df6f4f4a-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</ListBootstrapActionsResponse>"""

LIST_CLUSTERS_TEMPLATE = """<ListClustersResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ListClustersResult>
    <Clusters>
      {% for cluster in clusters %}
      <member>
        <Id>{{ cluster.id }}</Id>
        <Name>{{ cluster.name }}</Name>
        <NormalizedInstanceHours>{{ cluster.normalized_instance_hours }}</NormalizedInstanceHours>
        <Status>
          <State>{{ cluster.state }}</State>
          <StateChangeReason>
            <Code>USER_REQUEST</Code>
            {% if cluster.last_state_change_reason is not none %}
            <Message>{{ cluster.last_state_change_reason }}</Message>
            {% endif %}
          </StateChangeReason>
          <Timeline>
            <CreationDateTime>{{ cluster.creation_datetime.isoformat() }}</CreationDateTime>
            {% if cluster.end_datetime is not none %}
            <EndDateTime>{{ cluster.end_datetime.isoformat() }}</EndDateTime>
            {% endif %}
            {% if cluster.ready_datetime is not none %}
            <ReadyDateTime>{{ cluster.ready_datetime.isoformat() }}</ReadyDateTime>
            {% endif %}
          </Timeline>
        </Status>
      </member>
      {% endfor %}
    </Clusters>
    {% if marker is not none %}
    <Marker>{{ marker }}</Marker>
    {% endif %}
  </ListClustersResult>
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8418</RequestId>
  </ResponseMetadata>
</ListClustersResponse>"""

LIST_INSTANCE_GROUPS_TEMPLATE = """<ListInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ListInstanceGroupsResult>
    <InstanceGroups>
      {% for instance_group in instance_groups %}
      <member>
        {% if instance_group.bid_price is not none %}
        <BidPrice>{{ instance_group.bid_price }}</BidPrice>
        {% endif %}
        <Configurations/>
        <EbsBlockDevices/>
        {% if instance_group.ebs_optimized is not none %}
        <EbsOptimized>{{ instance_group.ebs_optimized }}</EbsOptimized>
        {% endif %}
        <Id>{{ instance_group.id }}</Id>
        <InstanceGroupType>{{ instance_group.role }}</InstanceGroupType>
        <InstanceType>{{ instance_group.type }}</InstanceType>
        <Market>{{ instance_group.market }}</Market>
        <Name>{{ instance_group.name }}</Name>
        <RequestedInstanceCount>{{ instance_group.num_instances }}</RequestedInstanceCount>
        <RunningInstanceCount>{{ instance_group.num_instances }}</RunningInstanceCount>
        <Status>
          <State>{{ instance_group.state }}</State>
          <StateChangeReason>
            {% if instance_group.state_change_reason is not none %}
            <Message>{{ instance_group.state_change_reason }}</Message>
            {% endif %}
            <Code>USER_REQUEST</Code>
          </StateChangeReason>
          <Timeline>
            <CreationDateTime>{{ instance_group.creation_datetime.isoformat() }}</CreationDateTime>
            {% if instance_group.end_datetime is not none %}
            <EndDateTime>{{ instance_group.end_datetime.isoformat() }}</EndDateTime>
            {% endif %}
            {% if instance_group.ready_datetime is not none %}
            <ReadyDateTime>{{ instance_group.ready_datetime.isoformat() }}</ReadyDateTime>
            {% endif %}
          </Timeline>
        </Status>
      </member>
      {% endfor %}
    </InstanceGroups>
    {% if marker is not none %}
    <Marker>{{ marker }}</Marker>
    {% endif %}
  </ListInstanceGroupsResult>
  <ResponseMetadata>
    <RequestId>8296d8b8-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</ListInstanceGroupsResponse>"""

LIST_STEPS_TEMPLATE = """<ListStepsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ListStepsResult>
    <Steps>
      {% for step in steps %}
      <member>
        <ActionOnFailure>{{ step.action_on_failure }}</ActionOnFailure>
        <Config>
          <Args>
            {% for arg in step.args %}
            <member>{{ arg | escape }}</member>
            {% endfor %}
          </Args>
          <Jar>{{ step.jar | escape }}</Jar>
          <MainClass/>
          <Properties>
            {% for key, val in step.properties.items() %}
            <member>
              <key>{{ key }}</key>
              <value>{{ val | escape }}</value>
            </member>
            {% endfor %}
          </Properties>
        </Config>
        <Id>{{ step.id }}</Id>
        <Name>{{ step.name | escape }}</Name>
        <Status>
<!-- does not exist for botocore 1.4.28
          <FailureDetails>
            <Reason/>
            <Message/>
            <LogFile/>
          </FailureDetails>
-->
          <State>{{ step.state }}</State>
          <StateChangeReason>{{ step.state_change_reason }}</StateChangeReason>
          <Timeline>
            <CreationDateTime>{{ step.creation_datetime.isoformat() }}</CreationDateTime>
            {% if step.end_datetime is not none %}
            <EndDateTime>{{ step.end_datetime.isoformat() }}</EndDateTime>
            {% endif %}
            {% if step.ready_datetime is not none %}
            <StartDateTime>{{ step.start_datetime.isoformat() }}</StartDateTime>
            {% endif %}
          </Timeline>
        </Status>
      </member>
      {% endfor %}
    </Steps>
    {% if marker is not none %}
    <Marker>{{ marker }}</Marker>
    {% endif %}
  </ListStepsResult>
  <ResponseMetadata>
    <RequestId>df6f4f4a-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</ListStepsResponse>"""

MODIFY_INSTANCE_GROUPS_TEMPLATE = """<ModifyInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</ModifyInstanceGroupsResponse>"""

REMOVE_TAGS_TEMPLATE = """<RemoveTagsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</RemoveTagsResponse>"""

RUN_JOB_FLOW_TEMPLATE = """<RunJobFlowResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <RunJobFlowResult>
    <JobFlowId>{{ cluster.id }}</JobFlowId>
  </RunJobFlowResult>
  <ResponseMetadata>
    <RequestId>8296d8b8-ed85-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</RunJobFlowResponse>"""

SET_TERMINATION_PROTECTION_TEMPLATE = """<SetTerminationProtection xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</SetTerminationProtection>"""

SET_VISIBLE_TO_ALL_USERS_TEMPLATE = """<SetVisibleToAllUsersResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</SetVisibleToAllUsersResponse>"""

TERMINATE_JOB_FLOWS_TEMPLATE = """<TerminateJobFlowsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <ResponseMetadata>
    <RequestId>2690d7eb-ed86-11dd-9877-6fad448a8419</RequestId>
  </ResponseMetadata>
</TerminateJobFlowsResponse>"""
