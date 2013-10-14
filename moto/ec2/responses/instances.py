from jinja2 import Template

from moto.core.utils import camelcase_to_underscores
from moto.ec2.models import ec2_backend
from moto.ec2.utils import instance_ids_from_querystring, filters_from_querystring, filter_reservations
from moto.ec2.exceptions import InvalidIdError


class InstanceResponse(object):
    def describe_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        if instance_ids:
            try:
                reservations = ec2_backend.get_reservations_by_instance_ids(instance_ids)
            except InvalidIdError as exc:
                template = Template(EC2_INVALID_INSTANCE_ID)
                return template.render(instance_id=exc.instance_id), dict(status=400)
        else:
            reservations = ec2_backend.all_reservations(make_copy=True)

        filter_dict = filters_from_querystring(self.querystring)
        reservations = filter_reservations(reservations, filter_dict)

        template = Template(EC2_DESCRIBE_INSTANCES)
        return template.render(reservations=reservations)

    def run_instances(self):
        min_count = int(self.querystring.get('MinCount', ['1'])[0])
        image_id = self.querystring.get('ImageId')[0]
        user_data = self.querystring.get('UserData')
        new_reservation = ec2_backend.add_instances(image_id, min_count, user_data)
        template = Template(EC2_RUN_INSTANCES)
        return template.render(reservation=new_reservation)

    def terminate_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.terminate_instances(instance_ids)
        template = Template(EC2_TERMINATE_INSTANCES)
        return template.render(instances=instances)

    def reboot_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.reboot_instances(instance_ids)
        template = Template(EC2_REBOOT_INSTANCES)
        return template.render(instances=instances)

    def stop_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.stop_instances(instance_ids)
        template = Template(EC2_STOP_INSTANCES)
        return template.render(instances=instances)

    def start_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.start_instances(instance_ids)
        template = Template(EC2_START_INSTANCES)
        return template.render(instances=instances)

    def describe_instance_attribute(self):
        # TODO this and modify below should raise IncorrectInstanceState if instance not in stopped state
        attribute = self.querystring.get("Attribute")[0]
        key = camelcase_to_underscores(attribute)
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        instance, value = ec2_backend.describe_instance_attribute(instance_id, key)
        template = Template(EC2_DESCRIBE_INSTANCE_ATTRIBUTE)
        return template.render(instance=instance, attribute=attribute, value=value)

    def modify_instance_attribute(self):
        for key, value in self.querystring.iteritems():
            if '.Value' in key:
                break

        value = self.querystring.get(key)[0]
        normalized_attribute = camelcase_to_underscores(key.split(".")[0])
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        ec2_backend.modify_instance_attribute(instance_id, normalized_attribute, value)
        return EC2_MODIFY_INSTANCE_ATTRIBUTE


EC2_RUN_INSTANCES = """<RunInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <reservationId>{{ reservation.id }}</reservationId>
  <ownerId>111122223333</ownerId>
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
          <privateDnsName/>
          <dnsName/>
          <reason/>
          <amiLaunchIndex>0</amiLaunchIndex>
          <instanceType>m1.small</instanceType>
          <launchTime>2007-08-07T11:51:50.000Z</launchTime>
          <placement>
            <availabilityZone>us-east-1b</availabilityZone>
            <groupName/>
            <tenancy>default</tenancy>
          </placement>
          <monitoring>
            <state>enabled</state>
          </monitoring>
          <sourceDestCheck>true</sourceDestCheck>
          <groupSet>
             <item>
                <groupId>sg-245f6a01</groupId>
                <groupName>default</groupName>
             </item>
          </groupSet>
          <virtualizationType>paravirtual</virtualizationType>
          <clientToken/>
          <hypervisor>xen</hypervisor>
          <ebsOptimized>false</ebsOptimized>
        </item>
    {% endfor %}
  </instancesSet>
  </RunInstancesResponse>"""

EC2_DESCRIBE_INSTANCES = """<DescribeInstancesResponse xmlns='http://ec2.amazonaws.com/doc/2012-12-01/'>
  <requestId>fdcdcab1-ae5c-489e-9c33-4637c5dda355</requestId>
      <reservationSet>
        {% for reservation in reservations %}
          <item>
            <reservationId>{{ reservation.id }}</reservationId>
            <ownerId>111122223333</ownerId>
            <groupSet>
              <item>
                <groupId>sg-1a2b3c4d</groupId>
                <groupName>my-security-group</groupName>
              </item>
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
                    <privateDnsName>ip-10.0.0.12.ec2.internal</privateDnsName>
                    <dnsName>ec2-46.51.219.63.compute-1.amazonaws.com</dnsName>
                    <reason/>
                    <keyName>gsg-keypair</keyName>
                    <amiLaunchIndex>0</amiLaunchIndex>
                    <productCodes/>
                    <instanceType>c1.medium</instanceType>
                    <launchTime>YYYY-MM-DDTHH:MM:SS+0000</launchTime>
                    <placement>
                      <availabilityZone>us-west-2a</availabilityZone>
                      <groupName/>
                      <tenancy>default</tenancy>
                    </placement>
                    <platform>windows</platform>
                    <monitoring>
                      <state>disabled</state>
                    </monitoring>
                    <subnetId>subnet-1a2b3c4d</subnetId>
                    <vpcId>vpc-1a2b3c4d</vpcId>
                    <privateIpAddress>10.0.0.12</privateIpAddress>
                    <ipAddress>46.51.219.63</ipAddress>
                    <sourceDestCheck>true</sourceDestCheck>
                    <groupSet>
                      <item>
                        <groupId>sg-1a2b3c4d</groupId>
                        <groupName>my-security-group</groupName>
                      </item>
                    </groupSet>
                    <architecture>x86_64</architecture>
                    <rootDeviceType>ebs</rootDeviceType>
                    <rootDeviceName>/dev/sda1</rootDeviceName>
                    <blockDeviceMapping />
                    <virtualizationType>hvm</virtualizationType>
                    <clientToken>ABCDE1234567890123</clientToken>
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
                    <hypervisor>xen</hypervisor>
                    <networkInterfaceSet />
                  </item>
                {% endfor %}
            </instancesSet>
          </item>
        {% endfor %}
      </reservationSet>
</DescribeInstancesResponse>"""

EC2_TERMINATE_INSTANCES = """
<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
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
<StopInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
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
<StartInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
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

EC2_REBOOT_INSTANCES = """<RebootInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RebootInstancesResponse>"""

EC2_DESCRIBE_INSTANCE_ATTRIBUTE = """<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>{{ instance.id }}</instanceId>
  <{{ attribute }}>
    <value>{{ value }}</value>
  </{{ attribute }}>
</DescribeInstanceAttributeResponse>"""

EC2_MODIFY_INSTANCE_ATTRIBUTE = """<ModifyInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ModifyInstanceAttributeResponse>"""


EC2_INVALID_INSTANCE_ID = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>InvalidInstanceID.NotFound</Code>
<Message>The instance ID '{{ instance_id }}' does not exist</Message></Error>
</Errors>
<RequestID>39070fe4-6f6d-4565-aecd-7850607e4555</RequestID></Response>"""
