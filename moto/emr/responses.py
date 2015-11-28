from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from .models import emr_backends
from .utils import tags_from_query_string


class ElasticMapReduceResponse(BaseResponse):

    @property
    def backend(self):
        return emr_backends[self.region]

    @property
    def boto3_request(self):
        return 'json' in self.headers.get('Content-Type', [])

    def add_job_flow_steps(self):
        job_flow_id = self._get_param('JobFlowId')
        steps = self._get_list_prefix('Steps.member')

        job_flow = self.backend.add_job_flow_steps(job_flow_id, steps)
        template = self.response_template(ADD_JOB_FLOW_STEPS_TEMPLATE)
        return template.render(job_flow=job_flow)

    def run_job_flow(self):
        flow_name = self._get_param('Name')
        log_uri = self._get_param('LogUri')
        steps = self._get_list_prefix('Steps.member')
        instance_attrs = self._get_dict_param('Instances.')
        job_flow_role = self._get_param('JobFlowRole')
        visible_to_all_users = self._get_param('VisibleToAllUsers')

        job_flow = self.backend.run_job_flow(
            flow_name, log_uri, job_flow_role,
            visible_to_all_users, steps, instance_attrs
        )
        instance_groups = self._get_list_prefix('Instances.InstanceGroups.member')
        if instance_groups:
            self.backend.add_instance_groups(job_flow.id, instance_groups)

        if self.boto3_request:
            return json.dumps({
                "JobFlowId": job_flow.id
            })

        template = self.response_template(RUN_JOB_FLOW_TEMPLATE)
        return template.render(job_flow=job_flow)

    def describe_job_flows(self):
        job_flow_ids = self._get_multi_param("JobFlowIds.member")
        job_flows = self.backend.describe_job_flows(job_flow_ids)
        template = self.response_template(DESCRIBE_JOB_FLOWS_TEMPLATE)
        return template.render(job_flows=job_flows)

    def terminate_job_flows(self):
        job_ids = self._get_multi_param('JobFlowIds.member.')
        job_flows = self.backend.terminate_job_flows(job_ids)
        template = self.response_template(TERMINATE_JOB_FLOWS_TEMPLATE)
        return template.render(job_flows=job_flows)

    def add_instance_groups(self):
        jobflow_id = self._get_param('JobFlowId')
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        instance_groups = self.backend.add_instance_groups(jobflow_id, instance_groups)
        template = self.response_template(ADD_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    def modify_instance_groups(self):
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        instance_groups = self.backend.modify_instance_groups(instance_groups)
        template = self.response_template(MODIFY_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    def set_visible_to_all_users(self):
        visible_to_all_users = self._get_param('VisibleToAllUsers')
        job_ids = self._get_multi_param('JobFlowIds.member')
        self.backend.set_visible_to_all_users(job_ids, visible_to_all_users)
        template = self.response_template(SET_VISIBLE_TO_ALL_USERS_TEMPLATE)
        return template.render()

    def set_termination_protection(self):
        termination_protection = self._get_param('TerminationProtected')
        job_ids = self._get_multi_param('JobFlowIds.member')
        self.backend.set_termination_protection(job_ids, termination_protection)
        template = self.response_template(SET_TERMINATION_PROTECTION_TEMPLATE)
        return template.render()

    def list_clusters(self):
        clusters = self.backend.list_clusters()

        if self.boto3_request:
            return json.dumps({
                "Clusters": [
                    {
                        "Id": cluster.id,
                        "Name": cluster.name,
                        "Status": {
                            "State": cluster.state,
                            "StatusChangeReason": {},
                            "TimeLine": {},
                        },
                        "NormalizedInstanceHours": cluster.normalized_instance_hours,
                    } for cluster in clusters
                ],
                "Marker": ""
            })

        template = self.response_template(LIST_CLUSTERS_TEMPLATE)
        return template.render(clusters=clusters)

    def describe_cluster(self):
        cluster_id = self._get_param('ClusterId')
        cluster = self.backend.get_cluster(cluster_id)
        template = self.response_template(DESCRIBE_CLUSTER_TEMPLATE)
        return template.render(cluster=cluster)

    def add_tags(self):
        cluster_id = self._get_param('ResourceId')
        tags = tags_from_query_string(self.querystring)
        self.backend.add_tags(cluster_id, tags)
        template = self.response_template(ADD_TAGS_TEMPLATE)
        return template.render()

    def remove_tags(self):
        cluster_id = self._get_param('ResourceId')
        tag_keys = self._get_multi_param('TagKeys.member')
        self.backend.remove_tags(cluster_id, tag_keys)
        template = self.response_template(REMOVE_TAGS_TEMPLATE)
        return template.render()


RUN_JOB_FLOW_TEMPLATE = """<RunJobFlowResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <RunJobFlowResult>
      <JobFlowId>{{ job_flow.id }}</JobFlowId>
   </RunJobFlowResult>
   <ResponseMetadata>
      <RequestId>
         8296d8b8-ed85-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</RunJobFlowResponse>"""

DESCRIBE_JOB_FLOWS_TEMPLATE = """<DescribeJobFlowsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <DescribeJobFlowsResult>
      <JobFlows>
         {% for job_flow in job_flows %}
         <member>
            <ExecutionStatusDetail>
               <CreationDateTime>2009-01-28T21:49:16Z</CreationDateTime>
               <StartDateTime>2009-01-28T21:49:16Z</StartDateTime>
               <State>{{ job_flow.state }}</State>
            </ExecutionStatusDetail>
            <Name>{{ job_flow.name }}</Name>
            <JobFlowRole>{{ job_flow.role }}</JobFlowRole>
            <LogUri>{{ job_flow.log_uri }}</LogUri>
            <Steps>
               {% for step in job_flow.steps %}
               <member>
                  <ExecutionStatusDetail>
                     <CreationDateTime>2009-01-28T21:49:16Z</CreationDateTime>
                     <State>{{ step.state }}</State>
                  </ExecutionStatusDetail>
                  <StepConfig>
                     <HadoopJarStep>
                        <Jar>{{ step.jar }}</Jar>
                        <MainClass>MyMainClass</MainClass>
                        <Args>
                           {% for arg in step.args %}
                           <member>{{ arg }}</member>
                           {% endfor %}
                        </Args>
                        <Properties/>
                     </HadoopJarStep>
                     <Name>{{ step.name }}</Name>
                     <ActionOnFailure>CONTINUE</ActionOnFailure>
                  </StepConfig>
               </member>
               {% endfor %}
            </Steps>
            <JobFlowId>{{ job_flow.id }}</JobFlowId>
            <Instances>
               <Placement>
                  <AvailabilityZone>us-east-1a</AvailabilityZone>
               </Placement>
               <SlaveInstanceType>{{ job_flow.slave_instance_type }}</SlaveInstanceType>
               <MasterInstanceType>{{ job_flow.master_instance_type }}</MasterInstanceType>
               <Ec2KeyName>{{ job_flow.ec2_key_name }}</Ec2KeyName>
               <NormalizedInstanceHours>{{ job_flow.normalized_instance_hours }}</NormalizedInstanceHours>
               <VisibleToAllUsers>{{ job_flow.visible_to_all_users }}</VisibleToAllUsers>
               <InstanceCount>{{ job_flow.instance_count }}</InstanceCount>
               <KeepJobFlowAliveWhenNoSteps>{{ job_flow.keep_job_flow_alive_when_no_steps }}</KeepJobFlowAliveWhenNoSteps>
               <TerminationProtected>{{ job_flow.termination_protected }}</TerminationProtected>
               <MasterPublicDnsName>ec2-184-0-0-1.us-west-1.compute.amazonaws.com</MasterPublicDnsName>
               <InstanceGroups>
                  {% for instance_group in job_flow.instance_groups %}
                  <member>
                    <InstanceGroupId>{{ instance_group.id }}</InstanceGroupId>
                    <InstanceRole>{{ instance_group.role }}</InstanceRole>
                    <InstanceRunningCount>{{ instance_group.num_instances }}</InstanceRunningCount>
                    <InstanceType>{{ instance_group.type }}</InstanceType>
                    <Market>{{ instance_group.market }}</Market>
                    <Name>{{ instance_group.name }}</Name>
                    <BidPrice>{{ instance_group.bid_price }}</BidPrice>
                  </member>
                  {% endfor %}
               </InstanceGroups>
            </Instances>
         </member>
         {% endfor %}
      </JobFlows>
   </DescribeJobFlowsResult>
   <ResponseMetadata>
      <RequestId>
         9cea3229-ed85-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</DescribeJobFlowsResponse>"""

TERMINATE_JOB_FLOWS_TEMPLATE = """<TerminateJobFlowsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</TerminateJobFlowsResponse>"""

ADD_JOB_FLOW_STEPS_TEMPLATE = """<AddJobFlowStepsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         df6f4f4a-ed85-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</AddJobFlowStepsResponse>"""

LIST_CLUSTERS_TEMPLATE = """<ListClustersResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
    <Clusters>
    {% for cluster in clusters %}
        <member>
            <Id>{{ cluster.id }}</Id>
            <Name>{{ cluster.name }}</Name>
            <NormalizedInstanceHours>{{ cluster.normalized_instance_hours }}</NormalizedInstanceHours>
            <Status>
                <State>{{ cluster.state }}</State>
                <StateChangeReason>
                    <Code></Code>
                    <Message></Message>
                </StateChangeReason>
                <Timeline></Timeline>
            </Status>
        </member>
    {% endfor %}
    </Clusters>
    <Marker></Marker>
    <ResponseMetadata>
        <RequestId>
            2690d7eb-ed86-11dd-9877-6fad448a8418
        </RequestId>
    </ResponseMetadata>
</ListClustersResponse>"""

DESCRIBE_CLUSTER_TEMPLATE = """<DescribeClusterResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
  <DescribeClusterResult>
    <Cluster>
      <Id>{{ cluster.id }}</Id>
      <Tags>
      {% for tag_key, tag_value in cluster.tags.items() %}
          <member>
              <Key>{{ tag_key }}</Key>
              <Value>{{ tag_value }}</Value>
          </member>
      {% endfor %}
      </Tags>
      <Ec2InstanceAttributes>
        <Ec2AvailabilityZone>{{ cluster.availability_zone }}</Ec2AvailabilityZone>
        <Ec2SubnetId>{{ cluster.subnet_id }}</Ec2SubnetId>
        <Ec2KeyName>{{ cluster.ec2_key_name }}</Ec2KeyName>
      </Ec2InstanceAttributes>
      <RunningAmiVersion>{{ cluster.running_ami_version }}</RunningAmiVersion>
      <VisibleToAllUsers>{{ cluster.visible_to_all_users }}</VisibleToAllUsers>
      <Status>
        <StateChangeReason>
          <Message>Terminated by user request</Message>
          <Code>USER_REQUEST</Code>
        </StateChangeReason>
        <State>{{ cluster.state }}</State>
        <Timeline>
          <CreationDateTime>2014-01-24T01:21:21Z</CreationDateTime>
          <ReadyDateTime>2014-01-24T01:25:26Z</ReadyDateTime>
          <EndDateTime>2014-01-24T02:19:46Z</EndDateTime>
        </Timeline>
      </Status>
      <AutoTerminate>{{ cluster.auto_terminate }}</AutoTerminate>
      <Name>{{ cluster.name }}</Name>
      <RequestedAmiVersion>{{ cluster.requested_ami_version }}</RequestedAmiVersion>
      <Applications>
        {% for application in cluster.applications %}
        <member>
          <Name>{{ application.name }}</Name>
          <Version>{{ application.version }}</Version>
        </member>
        {% endfor %}
      </Applications>
      <TerminationProtected>{{ cluster.termination_protection }}</TerminationProtected>
      <MasterPublicDnsName>ec2-184-0-0-1.us-west-1.compute.amazonaws.com</MasterPublicDnsName>
      <NormalizedInstanceHours>{{ cluster.normalized_instance_hours }}</NormalizedInstanceHours>
      <ServiceRole>{{ cluster.service_role }}</ServiceRole>
    </Cluster>
  </DescribeClusterResult>
  <ResponseMetadata>
    <RequestId>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</RequestId>
  </ResponseMetadata>
</DescribeClusterResponse>"""

ADD_INSTANCE_GROUPS_TEMPLATE = """<AddInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <InstanceGroupIds>{% for instance_group in instance_groups %}{{ instance_group.id }}{% if loop.index != loop.length %},{% endif %}{% endfor %}</InstanceGroupIds>
</AddInstanceGroupsResponse>"""

MODIFY_INSTANCE_GROUPS_TEMPLATE = """<ModifyInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</ModifyInstanceGroupsResponse>"""

SET_VISIBLE_TO_ALL_USERS_TEMPLATE = """<SetVisibleToAllUsersResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</SetVisibleToAllUsersResponse>"""


SET_TERMINATION_PROTECTION_TEMPLATE = """<SetTerminationProtection xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</SetTerminationProtection>"""

ADD_TAGS_TEMPLATE = """<AddTagsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</AddTagsResponse>"""

REMOVE_TAGS_TEMPLATE = """<RemoveTagsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</RemoveTagsResponse>"""
