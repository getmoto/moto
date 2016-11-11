from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from .models import iam_backend


class IamResponse(BaseResponse):

    def attach_role_policy(self):
        policy_arn = self._get_param('PolicyArn')
        role_name = self._get_param('RoleName')
        iam_backend.attach_role_policy(policy_arn, role_name)
        template = self.response_template(ATTACH_ROLE_POLICY_TEMPLATE)
        return template.render()

    def create_policy(self):
        description = self._get_param('Description')
        path = self._get_param('Path')
        policy_document = self._get_param('PolicyDocument')
        policy_name = self._get_param('PolicyName')
        policy = iam_backend.create_policy(description, path, policy_document, policy_name)
        template = self.response_template(CREATE_POLICY_TEMPLATE)
        return template.render(policy=policy)

    def list_attached_role_policies(self):
        marker = self._get_param('Marker')
        max_items = self._get_int_param('MaxItems', 100)
        path_prefix = self._get_param('PathPrefix', '/')
        role_name = self._get_param('RoleName')
        policies, marker = iam_backend.list_attached_role_policies(role_name, marker=marker, max_items=max_items, path_prefix=path_prefix)
        template = self.response_template(LIST_ATTACHED_ROLE_POLICIES_TEMPLATE)
        return template.render(policies=policies, marker=marker)

    def list_policies(self):
        marker = self._get_param('Marker')
        max_items = self._get_int_param('MaxItems', 100)
        only_attached = self._get_bool_param('OnlyAttached', False)
        path_prefix = self._get_param('PathPrefix', '/')
        scope = self._get_param('Scope', 'All')
        policies, marker = iam_backend.list_policies(marker, max_items, only_attached, path_prefix, scope)
        template = self.response_template(LIST_POLICIES_TEMPLATE)
        return template.render(policies=policies, marker=marker)

    def create_role(self):
        role_name = self._get_param('RoleName')
        path = self._get_param('Path')
        assume_role_policy_document = self._get_param('AssumeRolePolicyDocument')

        role = iam_backend.create_role(role_name, assume_role_policy_document, path)
        template = self.response_template(CREATE_ROLE_TEMPLATE)
        return template.render(role=role)

    def get_role(self):
        role_name = self._get_param('RoleName')
        role = iam_backend.get_role(role_name)

        template = self.response_template(GET_ROLE_TEMPLATE)
        return template.render(role=role)

    def list_role_policies(self):
        role_name = self._get_param('RoleName')
        role_policies_names = iam_backend.list_role_policies(role_name)
        template = self.response_template(LIST_ROLE_POLICIES)
        return template.render(role_policies=role_policies_names)

    def put_role_policy(self):
        role_name = self._get_param('RoleName')
        policy_name = self._get_param('PolicyName')
        policy_document = self._get_param('PolicyDocument')
        iam_backend.put_role_policy(role_name, policy_name, policy_document)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name="PutRolePolicyResponse")

    def get_role_policy(self):
        role_name = self._get_param('RoleName')
        policy_name = self._get_param('PolicyName')
        policy_name, policy_document = iam_backend.get_role_policy(role_name, policy_name)
        template = self.response_template(GET_ROLE_POLICY_TEMPLATE)
        return template.render(role_name=role_name,
                               policy_name=policy_name,
                               policy_document=policy_document)

    def update_assume_role_policy(self):
        role_name = self._get_param('RoleName')
        role = iam_backend.get_role(role_name)
        role.assume_role_policy_document = self._get_param('PolicyDocument')
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name="UpdateAssumeRolePolicyResponse")

    def create_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        path = self._get_param('Path')

        profile = iam_backend.create_instance_profile(profile_name, path, role_ids=[])
        template = self.response_template(CREATE_INSTANCE_PROFILE_TEMPLATE)
        return template.render(profile=profile)

    def get_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        profile = iam_backend.get_instance_profile(profile_name)

        template = self.response_template(GET_INSTANCE_PROFILE_TEMPLATE)
        return template.render(profile=profile)

    def add_role_to_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        role_name = self._get_param('RoleName')

        iam_backend.add_role_to_instance_profile(profile_name, role_name)
        template = self.response_template(ADD_ROLE_TO_INSTANCE_PROFILE_TEMPLATE)
        return template.render()

    def remove_role_from_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        role_name = self._get_param('RoleName')

        iam_backend.remove_role_from_instance_profile(profile_name, role_name)
        template = self.response_template(REMOVE_ROLE_FROM_INSTANCE_PROFILE_TEMPLATE)
        return template.render()

    def list_roles(self):
        roles = iam_backend.get_roles()

        template = self.response_template(LIST_ROLES_TEMPLATE)
        return template.render(roles=roles)

    def list_instance_profiles(self):
        profiles = iam_backend.get_instance_profiles()

        template = self.response_template(LIST_INSTANCE_PROFILES_TEMPLATE)
        return template.render(instance_profiles=profiles)

    def list_instance_profiles_for_role(self):
        role_name = self._get_param('RoleName')
        profiles = iam_backend.get_instance_profiles_for_role(role_name=role_name)

        template = self.response_template(LIST_INSTANCE_PROFILES_FOR_ROLE_TEMPLATE)
        return template.render(instance_profiles=profiles)

    def upload_server_certificate(self):
        cert_name = self._get_param('ServerCertificateName')
        cert_body = self._get_param('CertificateBody')
        path = self._get_param('Path')
        private_key = self._get_param('PrivateKey')
        cert_chain = self._get_param('CertificateName')

        cert = iam_backend.upload_server_cert(cert_name, cert_body, private_key, cert_chain=cert_chain, path=path)
        template = self.response_template(UPLOAD_CERT_TEMPLATE)
        return template.render(certificate=cert)

    def list_server_certificates(self, marker=None):
        certs = iam_backend.get_all_server_certs(marker=marker)
        template = self.response_template(LIST_SERVER_CERTIFICATES_TEMPLATE)
        return template.render(server_certificates=certs)

    def get_server_certificate(self):
        cert_name = self._get_param('ServerCertificateName')
        cert = iam_backend.get_server_certificate(cert_name)
        template = self.response_template(GET_SERVER_CERTIFICATE_TEMPLATE)
        return template.render(certificate=cert)

    def create_group(self):
        group_name = self._get_param('GroupName')
        path = self._get_param('Path')

        group = iam_backend.create_group(group_name, path)
        template = self.response_template(CREATE_GROUP_TEMPLATE)
        return template.render(group=group)

    def get_group(self):
        group_name = self._get_param('GroupName')

        group = iam_backend.get_group(group_name)
        template = self.response_template(GET_GROUP_TEMPLATE)
        return template.render(group=group)

    def list_groups(self):
        groups = iam_backend.list_groups()
        template = self.response_template(LIST_GROUPS_TEMPLATE)
        return template.render(groups=groups)

    def list_groups_for_user(self):
        user_name = self._get_param('UserName')

        groups = iam_backend.get_groups_for_user(user_name)
        template = self.response_template(LIST_GROUPS_FOR_USER_TEMPLATE)
        return template.render(groups=groups)

    def create_user(self):
        user_name = self._get_param('UserName')
        path = self._get_param('Path')

        user = iam_backend.create_user(user_name, path)
        template = self.response_template(USER_TEMPLATE)
        return template.render(action='Create', user=user)

    def get_user(self):
        user_name = self._get_param('UserName')
        user = iam_backend.get_user(user_name)
        template = self.response_template(USER_TEMPLATE)
        return template.render(action='Get', user=user)

    def list_users(self):
        path_prefix = self._get_param('PathPrefix')
        marker = self._get_param('Marker')
        max_items = self._get_param('MaxItems')
        user = iam_backend.list_users(path_prefix, marker, max_items)
        template = self.response_template(LIST_USERS_TEMPLATE)
        return template.render(action='List', user=user)

    def create_login_profile(self):
        user_name = self._get_param('UserName')
        password = self._get_param('Password')
        iam_backend.create_login_profile(user_name, password)

        template = self.response_template(CREATE_LOGIN_PROFILE_TEMPLATE)
        return template.render(user_name=user_name)

    def add_user_to_group(self):
        group_name = self._get_param('GroupName')
        user_name = self._get_param('UserName')

        iam_backend.add_user_to_group(group_name, user_name)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='AddUserToGroup')

    def remove_user_from_group(self):
        group_name = self._get_param('GroupName')
        user_name = self._get_param('UserName')

        iam_backend.remove_user_from_group(group_name, user_name)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='RemoveUserFromGroup')

    def get_user_policy(self):
        user_name = self._get_param('UserName')
        policy_name = self._get_param('PolicyName')

        policy_document = iam_backend.get_user_policy(user_name, policy_name)
        template = self.response_template(GET_USER_POLICY_TEMPLATE)
        return template.render(
            user_name=user_name,
            policy_name=policy_name,
            policy_document=policy_document
        )

    def put_user_policy(self):
        user_name = self._get_param('UserName')
        policy_name = self._get_param('PolicyName')
        policy_document = self._get_param('PolicyDocument')

        iam_backend.put_user_policy(user_name, policy_name, policy_document)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='PutUserPolicy')

    def delete_user_policy(self):
        user_name = self._get_param('UserName')
        policy_name = self._get_param('PolicyName')

        iam_backend.delete_user_policy(user_name, policy_name)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='DeleteUserPolicy')

    def create_access_key(self):
        user_name = self._get_param('UserName')

        key = iam_backend.create_access_key(user_name)
        template = self.response_template(CREATE_ACCESS_KEY_TEMPLATE)
        return template.render(key=key)

    def list_access_keys(self):
        user_name = self._get_param('UserName')

        keys = iam_backend.get_all_access_keys(user_name)
        template = self.response_template(LIST_ACCESS_KEYS_TEMPLATE)
        return template.render(user_name=user_name, keys=keys)

    def delete_access_key(self):
        user_name = self._get_param('UserName')
        access_key_id = self._get_param('AccessKeyId')

        iam_backend.delete_access_key(access_key_id, user_name)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='DeleteAccessKey')

    def delete_user(self):
        user_name = self._get_param('UserName')
        iam_backend.delete_user(user_name)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='DeleteUser')

    def delete_login_profile(self):
        user_name = self._get_param('UserName')
        iam_backend.delete_login_profile(user_name)
        template = self.response_template(GENERIC_EMPTY_TEMPLATE)
        return template.render(name='DeleteLoginProfile')

    def generate_credential_report(self):
        if iam_backend.report_generated():
            template = self.response_template(CREDENTIAL_REPORT_GENERATED)
        else:
            template = self.response_template(CREDENTIAL_REPORT_GENERATING)
        iam_backend.generate_report()
        return template.render()

    def get_credential_report(self):
        report = iam_backend.get_credential_report()
        template = self.response_template(CREDENTIAL_REPORT)
        return template.render(report=report)


ATTACH_ROLE_POLICY_TEMPLATE = """<AttachRolePolicyResponse>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</AttachRolePolicyResponse>"""

CREATE_POLICY_TEMPLATE = """<CreatePolicyResponse>
  <CreatePolicyResult>
    <Policy>
      <Arn>{{ policy.arn }}</Arn>
      <AttachmentCount>{{ policy.attachment_count }}</AttachmentCount>
      <CreateDate>{{ policy.create_datetime.isoformat() }}</CreateDate>
      <DefaultVersionId>{{ policy.default_version_id }}</DefaultVersionId>
      <Path>{{ policy.path }}</Path>
      <PolicyId>{{ policy.id }}</PolicyId>
      <PolicyName>{{ policy.name }}</PolicyName>
      <UpdateDate>{{ policy.update_datetime.isoformat() }}</UpdateDate>
    </Policy>
  </CreatePolicyResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</CreatePolicyResponse>"""

LIST_ATTACHED_ROLE_POLICIES_TEMPLATE = """<ListAttachedRolePoliciesResponse>
  <ListAttachedRolePoliciesResult>
    {% if marker is none %}
    <IsTruncated>false</IsTruncated>
    {% else %}
    <IsTruncated>true</IsTruncated>
    <Marker>{{ marker }}</Marker>
    {% endif %}
    <AttachedPolicies>
      {% for policy in policies %}
      <member>
        <PolicyName>{{ policy.name }}</PolicyName>
        <PolicyArn>{{ policy.arn }}</PolicyArn>
      </member>
      {% endfor %}
    </AttachedPolicies>
  </ListAttachedRolePoliciesResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</ListAttachedRolePoliciesResponse>"""

LIST_POLICIES_TEMPLATE = """<ListPoliciesResponse>
  <ListPoliciesResult>
    {% if marker is none %}
    <IsTruncated>false</IsTruncated>
    {% else %}
    <IsTruncated>true</IsTruncated>
    <Marker>{{ marker }}</Marker>
    {% endif %}
    <Policies>
      {% for policy in policies %}
      <member>
        <Arn>{{ policy.arn }}</Arn>
        <AttachmentCount>{{ policy.attachment_count }}</AttachmentCount>
        <CreateDate>{{ policy.create_datetime.isoformat() }}</CreateDate>
        <DefaultVersionId>{{ policy.default_version_id }}</DefaultVersionId>
        <Path>{{ policy.path }}</Path>
        <PolicyId>{{ policy.id }}</PolicyId>
        <PolicyName>{{ policy.name }}</PolicyName>
        <UpdateDate>{{ policy.update_datetime.isoformat() }}</UpdateDate>
      </member>
      {% endfor %}
    </Policies>
  </ListPoliciesResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</ListPoliciesResponse>"""

GENERIC_EMPTY_TEMPLATE = """<{{ name }}Response>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</{{ name }}Response>"""

CREATE_INSTANCE_PROFILE_TEMPLATE = """<CreateInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <CreateInstanceProfileResult>
    <InstanceProfile>
      <InstanceProfileId>{{ profile.id }}</InstanceProfileId>
      <Roles/>
      <InstanceProfileName>{{ profile.name }}</InstanceProfileName>
      <Path>{{ profile.path }}</Path>
      <Arn>arn:aws:iam::123456789012:instance-profile/application_abc/component_xyz/Webserver</Arn>
      <CreateDate>2012-05-09T16:11:10.222Z</CreateDate>
    </InstanceProfile>
  </CreateInstanceProfileResult>
  <ResponseMetadata>
    <RequestId>974142ee-99f1-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</CreateInstanceProfileResponse>"""

GET_INSTANCE_PROFILE_TEMPLATE = """<GetInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <GetInstanceProfileResult>
    <InstanceProfile>
      <InstanceProfileId>{{ profile.id }}</InstanceProfileId>
      <Roles>
        {% for role in profile.roles %}
        <member>
          <Path>{{ role.path }}</Path>
          <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
          <RoleName>{{ role.name }}</RoleName>
          <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
          <CreateDate>2012-05-09T15:45:35Z</CreateDate>
          <RoleId>{{ role.id }}</RoleId>
        </member>
        {% endfor %}
      </Roles>
      <InstanceProfileName>{{ profile.name }}</InstanceProfileName>
      <Path>{{ profile.path }}</Path>
      <Arn>arn:aws:iam::123456789012:instance-profile/application_abc/component_xyz/Webserver</Arn>
      <CreateDate>2012-05-09T16:11:10Z</CreateDate>
    </InstanceProfile>
  </GetInstanceProfileResult>
  <ResponseMetadata>
    <RequestId>37289fda-99f2-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</GetInstanceProfileResponse>"""

CREATE_ROLE_TEMPLATE = """<CreateRoleResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <CreateRoleResult>
    <Role>
      <Path>{{ role.path }}</Path>
      <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
      <RoleName>{{ role.name }}</RoleName>
      <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
      <CreateDate>2012-05-08T23:34:01.495Z</CreateDate>
      <RoleId>{{ role.id }}</RoleId>
    </Role>
  </CreateRoleResult>
  <ResponseMetadata>
    <RequestId>4a93ceee-9966-11e1-b624-b1aEXAMPLE7c</RequestId>
  </ResponseMetadata>
</CreateRoleResponse>"""

GET_ROLE_POLICY_TEMPLATE = """<GetRolePolicyResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
<GetRolePolicyResult>
  <PolicyName>{{ policy_name }}</PolicyName>
  <RoleName>{{ role_name }}</RoleName>
  <PolicyDocument>{{ policy_document }}</PolicyDocument>
</GetRolePolicyResult>
<ResponseMetadata>
  <RequestId>7e7cd8bc-99ef-11e1-a4c3-27EXAMPLE804</RequestId>
</ResponseMetadata>
</GetRolePolicyResponse>"""

GET_ROLE_TEMPLATE = """<GetRoleResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <GetRoleResult>
    <Role>
      <Path>{{ role.path }}</Path>
      <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
      <RoleName>{{ role.name }}</RoleName>
      <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
      <CreateDate>2012-05-08T23:34:01Z</CreateDate>
      <RoleId>{{ role.id }}</RoleId>
    </Role>
  </GetRoleResult>
  <ResponseMetadata>
    <RequestId>df37e965-9967-11e1-a4c3-270EXAMPLE04</RequestId>
  </ResponseMetadata>
</GetRoleResponse>"""

ADD_ROLE_TO_INSTANCE_PROFILE_TEMPLATE = """<AddRoleToInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ResponseMetadata>
    <RequestId>12657608-99f2-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</AddRoleToInstanceProfileResponse>"""

REMOVE_ROLE_FROM_INSTANCE_PROFILE_TEMPLATE = """<RemoveRoleFromInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ResponseMetadata>
    <RequestId>12657608-99f2-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</RemoveRoleFromInstanceProfileResponse>"""

LIST_ROLES_TEMPLATE = """<ListRolesResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ListRolesResult>
    <IsTruncated>false</IsTruncated>
    <Roles>
      {% for role in roles %}
      <member>
        <Path>{{ role.path }}</Path>
        <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
        <RoleName>{{ role.name }}</RoleName>
        <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
        <CreateDate>2012-05-09T15:45:35Z</CreateDate>
        <RoleId>{{ role.id }}</RoleId>
      </member>
      {% endfor %}
    </Roles>
  </ListRolesResult>
  <ResponseMetadata>
    <RequestId>20f7279f-99ee-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</ListRolesResponse>"""

LIST_ROLE_POLICIES = """<ListRolePoliciesResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
<ListRolePoliciesResult>
  <PolicyNames>
    {% for policy_name in role_policies %}
    <member>{{ policy_name }}</member>
    {% endfor %}
  </PolicyNames>
  <IsTruncated>false</IsTruncated>
</ListRolePoliciesResult>
<ResponseMetadata>
  <RequestId>8c7e1816-99f0-11e1-a4c3-27EXAMPLE804</RequestId>
</ResponseMetadata>
</ListRolePoliciesResponse>"""

LIST_INSTANCE_PROFILES_TEMPLATE = """<ListInstanceProfilesResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ListInstanceProfilesResult>
    <IsTruncated>false</IsTruncated>
    <InstanceProfiles>
      {% for instance in instance_profiles %}
      <member>
        <Id>{{ instance.id }}</Id>
        <Roles>
          {% for role in instance.roles %}
          <member>
            <Path>{{ role.path }}</Path>
            <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
            <RoleName>{{ role.name }}</RoleName>
            <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
            <CreateDate>2012-05-09T15:45:35Z</CreateDate>
            <RoleId>{{ role.id }}</RoleId>
          </member>
          {% endfor %}
        </Roles>
        <InstanceProfileName>{{ instance.name }}</InstanceProfileName>
        <Path>{{ instance.path }}</Path>
        <Arn>arn:aws:iam::123456789012:instance-profile/application_abc/component_xyz/Database</Arn>
        <CreateDate>2012-05-09T16:27:03Z</CreateDate>
      </member>
      {% endfor %}
    </InstanceProfiles>
  </ListInstanceProfilesResult>
  <ResponseMetadata>
    <RequestId>fd74fa8d-99f3-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</ListInstanceProfilesResponse>"""

UPLOAD_CERT_TEMPLATE = """<UploadServerCertificateResponse>
  <UploadServerCertificateResult>
    <ServerCertificateMetadata>
      <ServerCertificateName>{{ certificate.cert_name }}</ServerCertificateName>
      {% if certificate.path %}
      <Path>{{ certificate.path }}</Path>
      {% endif %}
      <Arn>arn:aws:iam::123456789012:server-certificate/{{ certificate.path }}/{{ certificate.cert_name }}</Arn>
      <UploadDate>2010-05-08T01:02:03.004Z</UploadDate>
      <ServerCertificateId>ASCACKCEVSQ6C2EXAMPLE</ServerCertificateId>
      <Expiration>2012-05-08T01:02:03.004Z</Expiration>
    </ServerCertificateMetadata>
  </UploadServerCertificateResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</UploadServerCertificateResponse>"""

LIST_SERVER_CERTIFICATES_TEMPLATE = """<ListServerCertificatesResponse>
  <ListServerCertificatesResult>
    <IsTruncated>false</IsTruncated>
    <ServerCertificateMetadataList>
      {% for certificate in server_certificates %}
      <member>
        <ServerCertificateMetadata>
          <ServerCertificateName>{{ certificate.cert_name }}</ServerCertificateName>
          {% if certificate.path %}
          <Path>{{ certificate.path }}</Path>
          <Arn>arn:aws:iam::123456789012:server-certificate/{{ certificate.path }}/{{ certificate.cert_name }}</Arn>
          {% else %}
          <Arn>arn:aws:iam::123456789012:server-certificate/{{ certificate.cert_name }}</Arn>
          {% endif %}
          <UploadDate>2010-05-08T01:02:03.004Z</UploadDate>
          <ServerCertificateId>ASCACKCEVSQ6C2EXAMPLE</ServerCertificateId>
          <Expiration>2012-05-08T01:02:03.004Z</Expiration>
        </ServerCertificateMetadata>
      </member>
      {% endfor %}
    </ServerCertificateMetadataList>
  </ListServerCertificatesResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</ListServerCertificatesResponse>"""

GET_SERVER_CERTIFICATE_TEMPLATE = """<GetServerCertificateResponse>
  <GetServerCertificateResult>
    <ServerCertificate>
      <ServerCertificateMetadata>
        <ServerCertificateName>{{ certificate.cert_name }}</ServerCertificateName>
        {% if certificate.path %}
        <Path>{{ certificate.path }}</Path>
        <Arn>arn:aws:iam::123456789012:server-certificate/{{ certificate.path }}/{{ certificate.cert_name }}</Arn>
        {% else %}
        <Arn>arn:aws:iam::123456789012:server-certificate/{{ certificate.cert_name }}</Arn>
        {% endif %}
        <UploadDate>2010-05-08T01:02:03.004Z</UploadDate>
        <ServerCertificateId>ASCACKCEVSQ6C2EXAMPLE</ServerCertificateId>
        <Expiration>2012-05-08T01:02:03.004Z</Expiration>
      </ServerCertificateMetadata>
      <CertificateBody>{{ certificate.cert_body }}</CertificateBody>
    </ServerCertificate>
  </GetServerCertificateResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</GetServerCertificateResponse>"""

CREATE_GROUP_TEMPLATE = """<CreateGroupResponse>
   <CreateGroupResult>
      <Group>
         <Path>{{ group.path }}</Path>
         <GroupName>{{ group.name }}</GroupName>
         <GroupId>{{ group.id }}</GroupId>
         <Arn>arn:aws:iam::123456789012:group/{{ group.path }}</Arn>
      </Group>
   </CreateGroupResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</CreateGroupResponse>"""

GET_GROUP_TEMPLATE = """<GetGroupResponse>
   <GetGroupResult>
      <Group>
         <Path>{{ group.path }}</Path>
         <GroupName>{{ group.name }}</GroupName>
         <GroupId>{{ group.id }}</GroupId>
         <Arn>arn:aws:iam::123456789012:group/{{ group.path }}</Arn>
      </Group>
      <Users>
        {% for user in group.users %}
          <member>
            <Path>{{ user.path }}</Path>
            <UserName>{{ user.name }}</UserName>
            <UserId>{{ user.id }}</UserId>
            <Arn>
            arn:aws:iam::123456789012:user/{{ user.path }}/{{ user.name}}
            </Arn>
          </member>
        {% endfor %}
      </Users>
      <IsTruncated>false</IsTruncated>
   </GetGroupResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</GetGroupResponse>"""

LIST_GROUPS_TEMPLATE = """<ListGroupsResponse>
  <ListGroupsResult>
    <Groups>
        {% for group in groups %}
        <member>
            <Path>{{ group.path }}</Path>
            <GroupName>{{ group.name }}</GroupName>
            <GroupId>{{ group.id }}</GroupId>
            <Arn>arn:aws:iam::123456789012:group/{{ group.path }}</Arn>
        </member>
        {% endfor %}
    </Groups>
    <IsTruncated>false</IsTruncated>
  </ListGroupsResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</ListGroupsResponse>"""

LIST_GROUPS_FOR_USER_TEMPLATE = """<ListGroupsForUserResponse>
  <ListGroupsForUserResult>
    <Groups>
        {% for group in groups %}
        <member>
            <Path>{{ group.path }}</Path>
            <GroupName>{{ group.name }}</GroupName>
            <GroupId>{{ group.id }}</GroupId>
            <Arn>arn:aws:iam::123456789012:group/{{ group.path }}</Arn>
        </member>
        {% endfor %}
    </Groups>
    <IsTruncated>false</IsTruncated>
  </ListGroupsForUserResult>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</ListGroupsForUserResponse>"""


USER_TEMPLATE = """<{{ action }}UserResponse>
   <{{ action }}UserResult>
      <User>
         <Path>{{ user.path }}</Path>
         <UserName>{{ user.name }}</UserName>
         <UserId>{{ user.id }}</UserId>
         <Arn>arn:aws:iam::123456789012:user/{{ user.path }}/{{ user.name }}</Arn>
     </User>
   </{{ action }}UserResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</{{ action }}UserResponse>"""

LIST_USERS_TEMPLATE = """<{{ action }}UsersResponse>
   <{{ action }}UsersResult>
      <Users>
         {% for user in users %}
         <member>
             <UserId>{{ user.id }}</UserId>
             <Path>{{ user.path }}</Path>
             <UserName>{{ user.name }}</UserName>
             <Arn>arn:aws:iam::123456789012:user/{{ user.path }}/{{ user.name }}</Arn>
         </member>
         {% endfor %}
     </Users>
   </{{ action }}UsersResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</{{ action }}UsersResponse>"""

CREATE_LOGIN_PROFILE_TEMPLATE = """
<CreateLoginProfileResponse>
   <CreateLoginProfileResult>
      <LoginProfile>
         <UserName>{{ user_name }}</UserName>
         <CreateDate>2011-09-19T23:00:56Z</CreateDate>
      </LoginProfile>
   </CreateLoginProfileResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</CreateLoginProfileResponse>
"""

GET_USER_POLICY_TEMPLATE = """<GetUserPolicyResponse>
   <GetUserPolicyResult>
      <UserName>{{ user_name }}</UserName>
      <PolicyName>{{ policy_name }}</PolicyName>
      <PolicyDocument>
      {{ policy_document }}
      </PolicyDocument>
   </GetUserPolicyResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</GetUserPolicyResponse>"""

CREATE_ACCESS_KEY_TEMPLATE = """<CreateAccessKeyResponse>
   <CreateAccessKeyResult>
     <AccessKey>
         <UserName>{{ key.user_name }}</UserName>
         <AccessKeyId>{{ key.access_key_id }}</AccessKeyId>
         <Status>{{ key.status }}</Status>
         <SecretAccessKey>
         {{ key.secret_access_key }}
         </SecretAccessKey>
      </AccessKey>
   </CreateAccessKeyResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</CreateAccessKeyResponse>"""

LIST_ACCESS_KEYS_TEMPLATE = """<ListAccessKeysResponse>
   <ListAccessKeysResult>
      <UserName>{{ user_name }}</UserName>
      <AccessKeyMetadata>
        {% for key in keys %}
         <member>
            <UserName>{{ user_name }}</UserName>
            <AccessKeyId>{{ key.access_key_id }}</AccessKeyId>
            <Status>{{ key.status }}</Status>
         </member>
        {% endfor %}
      </AccessKeyMetadata>
      <IsTruncated>false</IsTruncated>
   </ListAccessKeysResult>
   <ResponseMetadata>
      <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
   </ResponseMetadata>
</ListAccessKeysResponse>"""

CREDENTIAL_REPORT_GENERATING = """
<GenerateCredentialReportResponse>
    <GenerateCredentialReportResult>
        <state>STARTED</state>
        <description>No report exists. Starting a new report generation task</description>
    </GenerateCredentialReportResult>
    <ResponseMetadata>
        <RequestId>fa788a82-aa8a-11e4-a278-1786c418872b"</RequestId>
    </ResponseMetadata>
</GenerateCredentialReportResponse>"""

CREDENTIAL_REPORT_GENERATED = """<GenerateCredentialReportResponse>
    <GenerateCredentialReportResult>
        <state>COMPLETE</state>
    </GenerateCredentialReportResult>
    <ResponseMetadata>
        <RequestId>fa788a82-aa8a-11e4-a278-1786c418872b"</RequestId>
    </ResponseMetadata>
</GenerateCredentialReportResponse>"""

CREDENTIAL_REPORT = """<GetCredentialReportResponse>
    <GetCredentialReportResult>
        <content>{{ report }}</content>
        <GeneratedTime>2015-02-02T20:02:02Z</GeneratedTime>
        <ReportFormat>text/csv</ReportFormat>
    </GetCredentialReportResult>
    <ResponseMetadata>
        <RequestId>fa788a82-aa8a-11e4-a278-1786c418872b"</RequestId>
    </ResponseMetadata>
</GetCredentialReportResponse>"""

LIST_INSTANCE_PROFILES_FOR_ROLE_TEMPLATE = """<ListInstanceProfilesForRoleResponse>
<ListInstanceProfilesForRoleResult>
  <IsTruncated>false</IsTruncated>
  <InstanceProfiles>
    {% for profile in instance_profiles %}
    <member>
    <Id>{{ profile.id }}</Id>
      <Roles>
        {% for role in profile.roles %}
        <member>
          <Path>{{ role.path }}</Path>
          <Arn>arn:aws:iam::123456789012:role{{ role.path }}S3Access</Arn>
          <RoleName>{{ role.name }}</RoleName>
          <AssumeRolePolicyDocument>{{ role.assume_policy_document }}</AssumeRolePolicyDocument>
          <CreateDate>2012-05-09T15:45:35Z</CreateDate>
          <RoleId>{{ role.id }}</RoleId>
        </member>
        {% endfor %}
      </Roles>
      <InstanceProfileName>{{ profile.name }}</InstanceProfileName>
      <Path>{{ profile.path }}</Path>
      <Arn>arn:aws:iam::123456789012:instance-profile{{ profile.path }}Webserver</Arn>
      <CreateDate>2012-05-09T16:27:11Z</CreateDate>
    </member>
    {% endfor %}
  </InstanceProfiles>
</ListInstanceProfilesForRoleResult>
<ResponseMetadata>
  <RequestId>6a8c3992-99f4-11e1-a4c3-27EXAMPLE804</RequestId>
</ResponseMetadata>
</ListInstanceProfilesForRoleResponse>"""
