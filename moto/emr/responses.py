from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import emr_backend


class ElasticMapReduceResponse(BaseResponse):

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def _get_multi_param(self, param_prefix):
        return [value[0] for key, value in self.querystring.items() if key.startswith(param_prefix)]

    def _get_dict_param(self, param_prefix):
        params = {}
        for key, value in self.querystring.items():
            if key.startswith(param_prefix):
                params[camelcase_to_underscores(key.replace(param_prefix, ""))] = value[0]
        return params

    def _get_list_prefix(self, param_prefix):
        results = []
        param_index = 1
        while True:
            index_prefix = "{0}.{1}.".format(param_prefix, param_index)
            new_items = {}
            for key, value in self.querystring.items():
                if key.startswith(index_prefix):
                    new_items[camelcase_to_underscores(key.replace(index_prefix, ""))] = value[0]
            if not new_items:
                break
            results.append(new_items)
            param_index += 1
        return results

    def add_job_flow_steps(self):
        job_flow_id = self._get_param('JobFlowId')
        steps = self._get_list_prefix('Steps.member')

        job_flow = emr_backend.add_job_flow_steps(job_flow_id, steps)
        template = Template(ADD_JOB_FLOW_STEPS_TEMPLATE)
        return template.render(job_flow=job_flow)

    def run_job_flow(self):
        flow_name = self._get_param('Name')
        log_uri = self._get_param('LogUri')
        steps = self._get_list_prefix('Steps.member')
        instance_attrs = self._get_dict_param('Instances.')
        job_flow_role = self._get_param('JobFlowRole')
        visible_to_all_users = self._get_param('VisibleToAllUsers')

        job_flow = emr_backend.run_job_flow(
            flow_name, log_uri, job_flow_role,
            visible_to_all_users, steps, instance_attrs
        )
        template = Template(RUN_JOB_FLOW_TEMPLATE)
        return template.render(job_flow=job_flow)

    def describe_job_flows(self):
        job_flows = emr_backend.describe_job_flows()
        template = Template(DESCRIBE_JOB_FLOWS_TEMPLATE)
        return template.render(job_flows=job_flows)

    def terminate_job_flows(self):
        job_ids = self._get_multi_param('JobFlowIds.member.')
        job_flows = emr_backend.terminate_job_flows(job_ids)
        template = Template(TERMINATE_JOB_FLOWS_TEMPLATE)
        return template.render(job_flows=job_flows)

    def add_instance_groups(self):
        jobflow_id = self._get_param('JobFlowId')
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        instance_groups = emr_backend.add_instance_groups(jobflow_id, instance_groups)
        template = Template(ADD_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    def modify_instance_groups(self):
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        instance_groups = emr_backend.modify_instance_groups(instance_groups)
        template = Template(MODIFY_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    def set_visible_to_all_users(self):
        visible_to_all_users = self._get_param('VisibleToAllUsers')
        job_ids = self._get_multi_param('JobFlowIds.member')
        emr_backend.set_visible_to_all_users(job_ids, visible_to_all_users)
        template = Template(SET_VISIBLE_TO_ALL_USERS_TEMPLATE)
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
