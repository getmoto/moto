from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class SecurityGroups(object):
    def __init__(self, querystring):
        self.querystring = querystring

    def authorize_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.authorize_security_group_egress is not yet implemented')

    def authorize_security_group_ingress(self):
        raise NotImplementedError('SecurityGroups.authorize_security_group_ingress is not yet implemented')

    def create_security_group(self):
        name = self.querystring.get('GroupName')[0]
        description = self.querystring.get('GroupDescription')[0]
        group = ec2_backend.create_security_group(name, description)
        if not group:
            # There was an exisitng group
            return "There was an existing security group with name {}".format(name), dict(status=409)
        template = Template(CREATE_SECURITY_GROUP_RESPONSE)
        return template.render(group=group)

    def delete_security_group(self):
        name = self.querystring.get('GroupName')[0]
        group = ec2_backend.delete_security_group(name)

        if not group:
            # There was no such group
            return "There was no security group with name {}".format(name), dict(status=404)
        return DELETE_GROUP_RESPONSE

    def describe_security_groups(self):
        groups = ec2_backend.describe_security_groups()
        template = Template(DESCRIBE_SECURITY_GROUPS_RESPONSE)
        return template.render(groups=groups)

    def revoke_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.revoke_security_group_egress is not yet implemented')

    def revoke_security_group_ingress(self):
        raise NotImplementedError('SecurityGroups.revoke_security_group_ingress is not yet implemented')


CREATE_SECURITY_GROUP_RESPONSE = """<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
   <groupId>{{ group.id }}</groupId>
</CreateSecurityGroupResponse>"""

DELETE_GROUP_RESPONSE = """<DeleteSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSecurityGroupResponse>"""

DESCRIBE_SECURITY_GROUPS_RESPONSE = """<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <securityGroupInfo>
      {% for group in groups %}
          <item>
             <ownerId>111122223333</ownerId>
             <groupId>{{ group.id }}</groupId>
             <groupName>{{ group.name }}</groupName>
             <groupDescription>{{ group.description }}</groupDescription>
             <vpcId/>
             <ipPermissions>
                <item>
                   <ipProtocol>tcp</ipProtocol>
                   <fromPort>80</fromPort>
                   <toPort>80</toPort>
                   <groups/>
                   <ipRanges>
                      <item>
                         <cidrIp>0.0.0.0/0</cidrIp>
                      </item>
                   </ipRanges>
                </item>
             </ipPermissions>
             <ipPermissionsEgress/>
          </item>
      {% endfor %}
   </securityGroupInfo>
</DescribeSecurityGroupsResponse>"""