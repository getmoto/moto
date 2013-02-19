import boto

from urlparse import parse_qs

from jinja2 import Template

from .models import ec2_backend
from .utils import instance_ids_from_querystring


def instances(uri, body, headers):
    querystring = parse_qs(body)
    action = querystring['Action'][0]
    instance_ids = instance_ids_from_querystring(querystring)

    if action == 'DescribeInstances':
        template = Template(EC2_DESCRIBE_INSTANCES)
        return template.render(reservations=ec2_backend.all_reservations())
    elif action == 'RunInstances':
        min_count = int(querystring.get('MinCount', ['1'])[0])
        new_reservation = ec2_backend.add_instances(min_count)
        template = Template(EC2_RUN_INSTANCES)
        return template.render(reservation=new_reservation)
    elif action == 'TerminateInstances':
        instances = ec2_backend.terminate_instances(instance_ids)
        template = Template(EC2_TERMINATE_INSTANCES)
        return template.render(instances=instances)
    elif action == 'StopInstances':
        instances = ec2_backend.stop_instances(instance_ids)
        template = Template(EC2_STOP_INSTANCES)
        return template.render(instances=instances)
    elif action == 'StartInstances':
        instances = ec2_backend.start_instances(instance_ids)
        template = Template(EC2_START_INSTANCES)
        return template.render(instances=instances)
    # elif action == 'DescribeInstanceAttribute':
    #     attribute = querystring.get("Attribute")[0]
    #     instance_id = instance_ids[0]
    #     instance = ec2_backend.get_instance(instance_id)
    #     import pdb;pdb.set_trace()
    else:
        import pdb;pdb.set_trace()


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
          <imageId>ami-60a54009</imageId>
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
                    <imageId>ami-1a2b3c4d</imageId>
                    <instanceState>
                      <code>16</code>
                      <name>{{ instance.state }}</name>
                    </instanceState>
                    <privateDnsName/>
                    <dnsName/>
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
                    <blockDeviceMapping>
                      <item>
                        <deviceName>/dev/sda1</deviceName>
                        <ebs>
                          <volumeId>vol-1a2b3c4d</volumeId>
                          <status>attached</status>
                          <attachTime>YYYY-MM-DDTHH:MM:SS.SSSZ</attachTime>
                          <deleteOnTermination>true</deleteOnTermination>
                        </ebs>
                      </item>
                    </blockDeviceMapping>
                    <virtualizationType>hvm</virtualizationType>
                    <clientToken>ABCDE1234567890123</clientToken>
                    <tagSet>
                      <item>
                        <key>Name</key>
                        <value>Windows Instance</value>
                      </item>
                    </tagSet>
                    <hypervisor>xen</hypervisor>
                    <networkInterfaceSet>
                      <item>
                        <networkInterfaceId>eni-1a2b3c4d</networkInterfaceId>
                        <subnetId>subnet-1a2b3c4d</subnetId>
                        <vpcId>vpc-1a2b3c4d</vpcId>
                        <description>Primary network interface</description>
                        <ownerId>111122223333</ownerId>
                        <status>in-use</status>
                        <privateIpAddress>10.0.0.12</privateIpAddress>
                        <macAddress>1b:2b:3c:4d:5e:6f</macAddress>
                        <sourceDestCheck>true</sourceDestCheck>
                        <groupSet>
                          <item>
                            <groupId>sg-1a2b3c4d</groupId>
                            <groupName>my-security-group</groupName>
                          </item>
                        </groupSet>
                        <attachment>
                          <attachmentId>eni-attach-1a2b3c4d</attachmentId>
                          <deviceIndex>0</deviceIndex>
                          <status>attached</status>
                          <attachTime>YYYY-MM-DDTHH:MM:SS+0000</attachTime>
                          <deleteOnTermination>true</deleteOnTermination>
                        </attachment>
                        <association>
                          <publicIp>46.51.219.63</publicIp>
                          <ipOwnerId>111122223333</ipOwnerId>
                        </association>
                        <privateIpAddressesSet>
                          <item>
                            <privateIpAddress>10.0.0.12</privateIpAddress>
                            <primary>true</primary>
                            <association>
                              <publicIp>46.51.219.63</publicIp>
                              <ipOwnerId>111122223333</ipOwnerId>
                            </association>
                          </item>
                          <item>
                            <privateIpAddress>10.0.0.14</privateIpAddress>
                            <primary>false</primary>
                            <association>
                              <publicIp>46.51.221.177</publicIp>
                              <ipOwnerId>111122223333</ipOwnerId>
                            </association>
                          </item>
                        </privateIpAddressesSet>
                      </item>
                    </networkInterfaceSet>
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
        <currentState>
          <code>32</code>
          <name>shutting-down</name>
        </currentState>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
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
        <currentState>
          <code>32</code>
          <name>{{ instance.state }}</name>
        </currentState>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
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
        <currentState>
          <code>32</code>
          <name>{{ instance.state }}</name>
        </currentState>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
      </item>
    {% endfor %}
  </instancesSet>
</StartInstancesResponse>"""


EC2_DESCRIBE_INSTANCE_ATTRIBUTE = """<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>{{ instance.id }}</instanceId>
  <kernel>
    <value>aki-f70657b2</value>
  </kernel>
</DescribeInstanceAttributeResponse>"""
