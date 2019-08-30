from __future__ import unicode_literals
from boto.ec2.instancetype import InstanceType

from moto.autoscaling import autoscaling_backends
from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from moto.ec2.utils import filters_from_querystring, \
    dict_from_querystring


class InstanceResponse(BaseResponse):

    def describe_instances(self):
        filter_dict = filters_from_querystring(self.querystring)
        instance_ids = self._get_multi_param('InstanceId')
        token = self._get_param("NextToken")
        if instance_ids:
            reservations = self.ec2_backend.get_reservations_by_instance_ids(
                instance_ids, filters=filter_dict)
        else:
            reservations = self.ec2_backend.all_reservations(filters=filter_dict)

        reservation_ids = [reservation.id for reservation in reservations]
        if token:
            start = reservation_ids.index(token) + 1
        else:
            start = 0
        max_results = int(self._get_param('MaxResults', 100))
        reservations_resp = reservations[start:start + max_results]
        next_token = None
        if max_results and len(reservations) > (start + max_results):
            next_token = reservations_resp[-1].id
        template = self.response_template(EC2_DESCRIBE_INSTANCES)
        return template.render(reservations=reservations_resp, next_token=next_token).replace('True', 'true').replace('False', 'false')

    def run_instances(self):
        min_count = int(self._get_param('MinCount', if_none='1'))
        image_id = self._get_param('ImageId')
        owner_id = self._get_param('OwnerId')
        user_data = self._get_param('UserData')
        security_group_names = self._get_multi_param('SecurityGroup')
        security_group_ids = self._get_multi_param('SecurityGroupId')
        nics = dict_from_querystring("NetworkInterface", self.querystring)
        instance_type = self._get_param('InstanceType', if_none='m1.small')
        placement = self._get_param('Placement.AvailabilityZone')
        subnet_id = self._get_param('SubnetId')
        private_ip = self._get_param('PrivateIpAddress')
        associate_public_ip = self._get_param('AssociatePublicIpAddress')
        key_name = self._get_param('KeyName')
        ebs_optimized = self._get_param('EbsOptimized')
        instance_initiated_shutdown_behavior = self._get_param("InstanceInitiatedShutdownBehavior")
        tags = self._parse_tag_specification("TagSpecification")
        region_name = self.region

        if self.is_not_dryrun('RunInstance'):
            new_reservation = self.ec2_backend.add_instances(
                image_id, min_count, user_data, security_group_names,
                instance_type=instance_type, placement=placement, region_name=region_name, subnet_id=subnet_id,
                owner_id=owner_id, key_name=key_name, security_group_ids=security_group_ids,
                nics=nics, private_ip=private_ip, associate_public_ip=associate_public_ip,
                tags=tags, ebs_optimized=ebs_optimized, instance_initiated_shutdown_behavior=instance_initiated_shutdown_behavior)

            template = self.response_template(EC2_RUN_INSTANCES)
            return template.render(reservation=new_reservation)

    def terminate_instances(self):
        instance_ids = self._get_multi_param('InstanceId')
        if self.is_not_dryrun('TerminateInstance'):
            instances = self.ec2_backend.terminate_instances(instance_ids)
            autoscaling_backends[self.region].notify_terminate_instances(instance_ids)
            template = self.response_template(EC2_TERMINATE_INSTANCES)
            return template.render(instances=instances)

    def reboot_instances(self):
        instance_ids = self._get_multi_param('InstanceId')
        if self.is_not_dryrun('RebootInstance'):
            instances = self.ec2_backend.reboot_instances(instance_ids)
            template = self.response_template(EC2_REBOOT_INSTANCES)
            return template.render(instances=instances)

    def stop_instances(self):
        instance_ids = self._get_multi_param('InstanceId')
        if self.is_not_dryrun('StopInstance'):
            instances = self.ec2_backend.stop_instances(instance_ids)
            template = self.response_template(EC2_STOP_INSTANCES)
            return template.render(instances=instances)

    def start_instances(self):
        instance_ids = self._get_multi_param('InstanceId')
        if self.is_not_dryrun('StartInstance'):
            instances = self.ec2_backend.start_instances(instance_ids)
            template = self.response_template(EC2_START_INSTANCES)
            return template.render(instances=instances)

    def describe_instance_status(self):
        instance_ids = self._get_multi_param('InstanceId')
        include_all_instances = self._get_param('IncludeAllInstances') == 'true'

        if instance_ids:
            instances = self.ec2_backend.get_multi_instances_by_id(
                instance_ids)
        elif include_all_instances:
            instances = self.ec2_backend.all_instances()
        else:
            instances = self.ec2_backend.all_running_instances()

        template = self.response_template(EC2_INSTANCE_STATUS)
        return template.render(instances=instances)

    def describe_instance_types(self):
        instance_types = [InstanceType(
            name='t1.micro', cores=1, memory=644874240, disk=0)]
        template = self.response_template(EC2_DESCRIBE_INSTANCE_TYPES)
        return template.render(instance_types=instance_types)

    def describe_instance_attribute(self):
        # TODO this and modify below should raise IncorrectInstanceState if
        # instance not in stopped state
        attribute = self._get_param('Attribute')
        instance_id = self._get_param('InstanceId')
        instance, value = self.ec2_backend.describe_instance_attribute(
            instance_id, attribute)

        if attribute == "groupSet":
            template = self.response_template(
                EC2_DESCRIBE_INSTANCE_GROUPSET_ATTRIBUTE)
        else:
            template = self.response_template(EC2_DESCRIBE_INSTANCE_ATTRIBUTE)

        return template.render(instance=instance, attribute=attribute, value=value)

    def modify_instance_attribute(self):
        handlers = [self._dot_value_instance_attribute_handler,
                    self._block_device_mapping_handler,
                    self._security_grp_instance_attribute_handler]

        for handler in handlers:
            success = handler()
            if success:
                return success

        msg = "This specific call to ModifyInstanceAttribute has not been" \
              " implemented in Moto yet. Feel free to open an issue at" \
              " https://github.com/spulec/moto/issues"
        raise NotImplementedError(msg)

    def _block_device_mapping_handler(self):
        """
        Handles requests which are generated by code similar to:

            instance.modify_attribute(
                BlockDeviceMappings=[{
                    'DeviceName': '/dev/sda1',
                    'Ebs': {'DeleteOnTermination': True}
                }]
            )

        The querystring contains information similar to:

            BlockDeviceMapping.1.Ebs.DeleteOnTermination : ['true']
            BlockDeviceMapping.1.DeviceName : ['/dev/sda1']

        For now we only support the "BlockDeviceMapping.1.Ebs.DeleteOnTermination"
        configuration, but it should be trivial to add anything else.
        """
        mapping_counter = 1
        mapping_device_name_fmt = 'BlockDeviceMapping.%s.DeviceName'
        mapping_del_on_term_fmt = 'BlockDeviceMapping.%s.Ebs.DeleteOnTermination'
        while True:
            mapping_device_name = mapping_device_name_fmt % mapping_counter
            if mapping_device_name not in self.querystring.keys():
                break

            mapping_del_on_term = mapping_del_on_term_fmt % mapping_counter
            del_on_term_value_str = self.querystring[mapping_del_on_term][0]
            del_on_term_value = True if 'true' == del_on_term_value_str else False
            device_name_value = self.querystring[mapping_device_name][0]

            instance_id = self._get_param('InstanceId')
            instance = self.ec2_backend.get_instance(instance_id)

            if self.is_not_dryrun('ModifyInstanceAttribute'):
                block_device_type = instance.block_device_mapping[
                    device_name_value]
                block_device_type.delete_on_termination = del_on_term_value

            # +1 for the next device
            mapping_counter += 1

        if mapping_counter > 1:
            return EC2_MODIFY_INSTANCE_ATTRIBUTE

    def _dot_value_instance_attribute_handler(self):
        attribute_key = None
        for key, value in self.querystring.items():
            if '.Value' in key:
                attribute_key = key
                break

        if not attribute_key:
            return

        if self.is_not_dryrun('Modify' + attribute_key.split(".")[0]):
            value = self.querystring.get(attribute_key)[0]
            normalized_attribute = camelcase_to_underscores(
                attribute_key.split(".")[0])
            instance_id = self._get_param('InstanceId')
            self.ec2_backend.modify_instance_attribute(
                instance_id, normalized_attribute, value)
            return EC2_MODIFY_INSTANCE_ATTRIBUTE

    def _security_grp_instance_attribute_handler(self):
        new_security_grp_list = []
        for key, value in self.querystring.items():
            if 'GroupId.' in key:
                new_security_grp_list.append(self.querystring.get(key)[0])

        instance_id = self._get_param('InstanceId')
        if self.is_not_dryrun('ModifyInstanceSecurityGroups'):
            self.ec2_backend.modify_instance_security_groups(
                instance_id, new_security_grp_list)
            return EC2_MODIFY_INSTANCE_ATTRIBUTE


EC2_RUN_INSTANCES = """<RunInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <reservationId>{{ reservation.id }}</reservationId>
  <ownerId>123456789012</ownerId>
  <groupSet>
    <item>
      <groupId>sg-245f6a01</groupId>
      <groupName>default</groupName>
    </item>
  </groupSet>
  <instancesSet>
    {% for instance in reservation.instances %}
        <item>
          <instanceId>{{ instance.id }}</instanceId>
          <imageId>{{ instance.image_id }}</imageId>
          <instanceState>
            <code>0</code>
            <name>pending</name>
         </instanceState>
          <privateDnsName>{{ instance.private_dns }}</privateDnsName>
          <publicDnsName>{{ instance.public_dns }}</publicDnsName>
          <dnsName>{{ instance.public_dns }}</dnsName>
          <reason/>
          <keyName>{{ instance.key_name }}</keyName>
          <ebsOptimized>{{ instance.ebs_optimized }}</ebsOptimized>
          <amiLaunchIndex>{{ instance.ami_launch_index }}</amiLaunchIndex>
          <instanceType>{{ instance.instance_type }}</instanceType>
          <launchTime>{{ instance.launch_time }}</launchTime>
          <placement>
            <availabilityZone>{{ instance.placement}}</availabilityZone>
            <groupName/>
            <tenancy>default</tenancy>
          </placement>
          <monitoring>
            <state>enabled</state>
          </monitoring>
          {% if instance.subnet_id %}
            <subnetId>{{ instance.subnet_id }}</subnetId>
          {% elif instance.nics[0].subnet.id %}
            <subnetId>{{ instance.nics[0].subnet.id }}</subnetId>
          {% endif %}
          {% if instance.vpc_id %}
            <vpcId>{{ instance.vpc_id }}</vpcId>
          {% elif instance.nics[0].subnet.vpc_id %}
            <vpcId>{{ instance.nics[0].subnet.vpc_id }}</vpcId>
          {% endif %}
          <privateIpAddress>{{ instance.private_ip }}</privateIpAddress>
          {% if instance.nics[0].public_ip %}
              <ipAddress>{{ instance.nics[0].public_ip }}</ipAddress>
          {% endif %}
          <sourceDestCheck>{{ instance.source_dest_check }}</sourceDestCheck>
          <groupSet>
             {% for group in instance.dynamic_group_list %}
             <item>
                <groupId>{{ group.id }}</groupId>
                <groupName>{{ group.name }}</groupName>
             </item>
             {% endfor %}
          </groupSet>
          {% if instance.platform %}
          <platform>{{ instance.platform }}</platform>
          {% endif %}
          <virtualizationType>{{ instance.virtualization_type }}</virtualizationType>
          <architecture>{{ instance.architecture }}</architecture>
          <kernelId>{{ instance.kernel }}</kernelId>
          <clientToken/>
          <hypervisor>xen</hypervisor>
          <ebsOptimized>false</ebsOptimized>
          <tagSet>
            {% for tag in instance.get_tags() %}
              <item>
                <key>{{ tag.key }}</key>
                <value>{{ tag.value }}</value>
              </item>
            {% endfor %}
          </tagSet>
          <networkInterfaceSet>
            {% for nic in instance.nics.values() %}
              <item>
                <networkInterfaceId>{{ nic.id }}</networkInterfaceId>
                {% if nic.subnet %}
                  <subnetId>{{ nic.subnet.id }}</subnetId>
                  <vpcId>{{ nic.subnet.vpc_id }}</vpcId>
                {% endif %}
                <description>Primary network interface</description>
                <ownerId>123456789012</ownerId>
                <status>in-use</status>
                <macAddress>1b:2b:3c:4d:5e:6f</macAddress>
                <privateIpAddress>{{ nic.private_ip_address }}</privateIpAddress>
                <sourceDestCheck>{{ instance.source_dest_check }}</sourceDestCheck>
                <groupSet>
                  {% for group in nic.group_set %}
                  <item>
                    <groupId>{{ group.id }}</groupId>
                    <groupName>{{ group.name }}</groupName>
                  </item>
                  {% endfor %}
                </groupSet>
                <attachment>
                  <attachmentId>{{ nic.attachment_id }}</attachmentId>
                  <deviceIndex>{{ nic.device_index }}</deviceIndex>
                  <status>attached</status>
                  <attachTime>2015-01-01T00:00:00Z</attachTime>
                  <deleteOnTermination>true</deleteOnTermination>
                </attachment>
                {% if nic.public_ip %}
                  <association>
                    <publicIp>{{ nic.public_ip }}</publicIp>
                    <ipOwnerId>123456789012</ipOwnerId>
                  </association>
                {% endif %}
                <privateIpAddressesSet>
                  <item>
                    <privateIpAddress>{{ nic.private_ip_address }}</privateIpAddress>
                    <primary>true</primary>
                    {% if nic.public_ip %}
                      <association>
                        <publicIp>{{ nic.public_ip }}</publicIp>
                        <ipOwnerId>123456789012</ipOwnerId>
                      </association>
                    {% endif %}
                  </item>
                </privateIpAddressesSet>
              </item>
            {% endfor %}
          </networkInterfaceSet>
        </item>
    {% endfor %}
  </instancesSet>
  </RunInstancesResponse>"""

EC2_DESCRIBE_INSTANCES = """<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>fdcdcab1-ae5c-489e-9c33-4637c5dda355</requestId>
      <reservationSet>
        {% for reservation in reservations %}
          <item>
            <reservationId>{{ reservation.id }}</reservationId>
            <ownerId>123456789012</ownerId>
            <groupSet>
              {% for group in reservation.dynamic_group_list %}
              <item>
      {% if group.id %}
                <groupId>{{ group.id }}</groupId>
                <groupName>{{ group.name }}</groupName>
                {% else %}
                <groupId>{{ group }}</groupId>
                {% endif %}
              </item>
              {% endfor %}
            </groupSet>
            <instancesSet>
                {% for instance in reservation.instances %}
                  <item>
                    <instanceId>{{ instance.id }}</instanceId>
                    <imageId>{{ instance.image_id }}</imageId>
                    <instanceState>
                      <code>{{ instance._state.code }}</code>
                      <name>{{ instance._state.name }}</name>
                    </instanceState>
                    <privateDnsName>{{ instance.private_dns }}</privateDnsName>
                    <publicDnsName>{{ instance.public_dns }}</publicDnsName>
                    <dnsName>{{ instance.public_dns }}</dnsName>
                    <reason>{{ instance._reason }}</reason>
                    <keyName>{{ instance.key_name }}</keyName>
                    <ebsOptimized>{{ instance.ebs_optimized }}</ebsOptimized>
                    <amiLaunchIndex>{{ instance.ami_launch_index }}</amiLaunchIndex>
                    <productCodes/>
                    <instanceType>{{ instance.instance_type }}</instanceType>
                    <launchTime>{{ instance.launch_time }}</launchTime>
                    <placement>
                      <availabilityZone>{{ instance.placement }}</availabilityZone>
                      <groupName/>
                      <tenancy>default</tenancy>
                    </placement>
                    {% if instance.platform %}
                    <platform>{{ instance.platform }}</platform>
                    {% endif %}
                    <monitoring>
                      <state>disabled</state>
                    </monitoring>
                    {% if instance.subnet_id %}
                      <subnetId>{{ instance.subnet_id }}</subnetId>
                    {% elif instance.nics[0].subnet.id %}
                      <subnetId>{{ instance.nics[0].subnet.id }}</subnetId>
                    {% endif %}
                    {% if instance.vpc_id %}
                      <vpcId>{{ instance.vpc_id }}</vpcId>
                    {% elif instance.nics[0].subnet.vpc_id %}
                      <vpcId>{{ instance.nics[0].subnet.vpc_id }}</vpcId>
                    {% endif %}
                    <privateIpAddress>{{ instance.private_ip }}</privateIpAddress>
                    {% if instance.nics[0].public_ip %}
                        <ipAddress>{{ instance.nics[0].public_ip }}</ipAddress>
                    {% endif %}
                    <sourceDestCheck>{{ instance.source_dest_check }}</sourceDestCheck>
                    <groupSet>
                      {% for group in instance.dynamic_group_list %}
                      <item>
                      {% if group.id %}
                      <groupId>{{ group.id }}</groupId>
                      <groupName>{{ group.name }}</groupName>
                      {% else %}
                      <groupId>{{ group }}</groupId>
                      {% endif %}
                      </item>
                      {% endfor %}
                    </groupSet>
                    <stateReason>
                      <code>{{ instance._state_reason.code }}</code>
                      <message>{{ instance._state_reason.message }}</message>
                    </stateReason>
                    <architecture>{{ instance.architecture }}</architecture>
                    <kernelId>{{ instance.kernel }}</kernelId>
                    <rootDeviceType>ebs</rootDeviceType>
                    <rootDeviceName>/dev/sda1</rootDeviceName>
                    <blockDeviceMapping>
                        {% for device_name,deviceobject in instance.get_block_device_mapping %}
                      <item>
                         <deviceName>{{ device_name }}</deviceName>
                          <ebs>
                             <volumeId>{{ deviceobject.volume_id }}</volumeId>
                             <status>{{ deviceobject.status }}</status>
                             <attachTime>{{ deviceobject.attach_time }}</attachTime>
                             <deleteOnTermination>{{ deviceobject.delete_on_termination }}</deleteOnTermination>
                             <size>{{deviceobject.size}}</size>
                        </ebs>
                      </item>
                     {% endfor %}
                    </blockDeviceMapping>
                    <virtualizationType>{{ instance.virtualization_type }}</virtualizationType>
                    <clientToken>ABCDE1234567890123</clientToken>
                    {% if instance.get_tags() %}
                    <tagSet>
                      {% for tag in instance.get_tags() %}
                        <item>
                          <resourceId>{{ tag.resource_id }}</resourceId>
                          <resourceType>{{ tag.resource_type }}</resourceType>
                          <key>{{ tag.key }}</key>
                          <value>{{ tag.value }}</value>
                        </item>
                      {% endfor %}
                    </tagSet>
                    {% endif %}
                    <hypervisor>xen</hypervisor>
                    <networkInterfaceSet>
                      {% for nic in instance.nics.values() %}
                        <item>
                          <networkInterfaceId>{{ nic.id }}</networkInterfaceId>
                          {% if nic.subnet %}
                            <subnetId>{{ nic.subnet.id }}</subnetId>
                            <vpcId>{{ nic.subnet.vpc_id }}</vpcId>
                          {% endif %}
                          <description>Primary network interface</description>
                          <ownerId>123456789012</ownerId>
                          <status>in-use</status>
                          <macAddress>1b:2b:3c:4d:5e:6f</macAddress>
                          <privateIpAddress>{{ nic.private_ip_address }}</privateIpAddress>
                          <sourceDestCheck>{{ instance.source_dest_check }}</sourceDestCheck>
                          <groupSet>
                            {% for group in nic.group_set %}
                            <item>
               {% if group.id %}
               <groupId>{{ group.id }}</groupId>
               <groupName>{{ group.name }}</groupName>
               {% else %}
               <groupId>{{ group }}</groupId>
               {% endif %}
                            </item>
                            {% endfor %}
                          </groupSet>
                          <attachment>
                            <attachmentId>{{ nic.attachment_id }}</attachmentId>
                            <deviceIndex>{{ nic.device_index }}</deviceIndex>
                            <status>attached</status>
                            <attachTime>2015-01-01T00:00:00Z</attachTime>
                            <deleteOnTermination>true</deleteOnTermination>
                          </attachment>
                          {% if nic.public_ip %}
                            <association>
                              <publicIp>{{ nic.public_ip }}</publicIp>
                              <ipOwnerId>123456789012</ipOwnerId>
                            </association>
                          {% endif %}
                          <privateIpAddressesSet>
                            <item>
                              <privateIpAddress>{{ nic.private_ip_address }}</privateIpAddress>
                              <primary>true</primary>
                              {% if nic.public_ip %}
                                <association>
                                  <publicIp>{{ nic.public_ip }}</publicIp>
                                  <ipOwnerId>123456789012</ipOwnerId>
                                </association>
                              {% endif %}
                            </item>
                          </privateIpAddressesSet>
                        </item>
                      {% endfor %}
                    </networkInterfaceSet>
                  </item>
                {% endfor %}
            </instancesSet>
          </item>
        {% endfor %}
      </reservationSet>
      {% if next_token %}
      <nextToken>{{ next_token }}</nextToken>
      {% endif %}
</DescribeInstancesResponse>"""

EC2_TERMINATE_INSTANCES = """
<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instancesSet>
    {% for instance in instances %}
      <item>
        <instanceId>{{ instance.id }}</instanceId>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
        <currentState>
          <code>32</code>
          <name>shutting-down</name>
        </currentState>
      </item>
    {% endfor %}
  </instancesSet>
</TerminateInstancesResponse>"""

EC2_STOP_INSTANCES = """
<StopInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instancesSet>
    {% for instance in instances %}
      <item>
        <instanceId>{{ instance.id }}</instanceId>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
        <currentState>
          <code>64</code>
          <name>stopping</name>
        </currentState>
      </item>
    {% endfor %}
  </instancesSet>
</StopInstancesResponse>"""

EC2_START_INSTANCES = """
<StartInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instancesSet>
    {% for instance in instances %}
      <item>
        <instanceId>{{ instance.id }}</instanceId>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
        <currentState>
          <code>0</code>
          <name>pending</name>
        </currentState>
      </item>
    {% endfor %}
  </instancesSet>
</StartInstancesResponse>"""

EC2_REBOOT_INSTANCES = """<RebootInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RebootInstancesResponse>"""

EC2_DESCRIBE_INSTANCE_ATTRIBUTE = """<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>{{ instance.id }}</instanceId>
  <{{ attribute }}>
    {% if value is not none %}
    <value>{{ value }}</value>
    {% endif %}
  </{{ attribute }}>
</DescribeInstanceAttributeResponse>"""

EC2_DESCRIBE_INSTANCE_GROUPSET_ATTRIBUTE = """<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>{{ instance.id }}</instanceId>
  <{{ attribute }}>
    {% for sg in value %}
      <item>
        <groupId>{{ sg.id }}</groupId>
      </item>
    {% endfor %}
  </{{ attribute }}>
</DescribeInstanceAttributeResponse>"""

EC2_MODIFY_INSTANCE_ATTRIBUTE = """<ModifyInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ModifyInstanceAttributeResponse>"""

EC2_INSTANCE_STATUS = """<?xml version="1.0" encoding="UTF-8"?>
<DescribeInstanceStatusResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
    <instanceStatusSet>
      {% for instance in instances %}
        <item>
            <instanceId>{{ instance.id }}</instanceId>
            <availabilityZone>{{ instance.placement }}</availabilityZone>
            <instanceState>
                <code>{{ instance.state_code }}</code>
                <name>{{ instance.state }}</name>
            </instanceState>
            {% if instance.state_code == 16 %}
              <systemStatus>
                  <status>ok</status>
                  <details>
                      <item>
                          <name>reachability</name>
                          <status>passed</status>
                      </item>
                  </details>
              </systemStatus>
              <instanceStatus>
                  <status>ok</status>
                  <details>
                      <item>
                          <name>reachability</name>
                          <status>passed</status>
                      </item>
                  </details>
              </instanceStatus>
            {% else %}
              <systemStatus>
                  <status>not-applicable</status>
              </systemStatus>
              <instanceStatus>
                  <status>not-applicable</status>
              </instanceStatus>
            {% endif %}
        </item>
      {% endfor %}
    </instanceStatusSet>
</DescribeInstanceStatusResponse>"""

EC2_DESCRIBE_INSTANCE_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<DescribeInstanceTypesResponse xmlns="http://api.outscale.com/wsdl/fcuext/2014-04-15/">
    <requestId>f8b86168-d034-4e65-b48d-3b84c78e64af</requestId>
    <instanceTypeSet>
    {% for instance_type in instance_types %}
        <item>
            <name>{{ instance_type.name }}</name>
            <vcpu>{{ instance_type.cores }}</vcpu>
            <memory>{{ instance_type.memory }}</memory>
            <storageSize>{{ instance_type.disk }}</storageSize>
            <storageCount>{{ instance_type.storageCount }}</storageCount>
            <maxIpAddresses>{{ instance_type.maxIpAddresses }}</maxIpAddresses>
            <ebsOptimizedAvailable>{{ instance_type.ebsOptimizedAvailable }}</ebsOptimizedAvailable>
        </item>
    {% endfor %}
    </instanceTypeSet>
</DescribeInstanceTypesResponse>"""
