from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import iam_backend


class IamResponse(BaseResponse):

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def create_role(self):
        role_name = self._get_param('RoleName')
        path = self._get_param('Path')
        assume_role_policy_document = self._get_param('AssumeRolePolicyDocument')

        role = iam_backend.create_role(role_name, assume_role_policy_document, path, policies=[])
        template = Template(CREATE_ROLE_TEMPLATE)
        return template.render(role=role)

    def get_role(self):
        role_name = self._get_param('RoleName')
        role = iam_backend.get_role(role_name)

        template = Template(GET_ROLE_TEMPLATE)
        return template.render(role=role)

    def create_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        path = self._get_param('Path')

        profile = iam_backend.create_instance_profile(profile_name, path, role_ids=[])
        template = Template(CREATE_INSTANCE_PROFILE_TEMPLATE)
        return template.render(profile=profile)

    def get_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        profile = iam_backend.get_instance_profile(profile_name)

        template = Template(GET_INSTANCE_PROFILE_TEMPLATE)
        return template.render(profile=profile)

    def add_role_to_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        role_name = self._get_param('RoleName')

        iam_backend.add_role_to_instance_profile(profile_name, role_name)
        template = Template(ADD_ROLE_TO_INSTANCE_PROFILE_TEMPLATE)
        return template.render()

    def list_roles(self):
        roles = iam_backend.get_roles()

        template = Template(LIST_ROLES_TEMPLATE)
        return template.render(roles=roles)

    def list_instance_profiles(self):
        profiles = iam_backend.get_instance_profiles()

        template = Template(LIST_INSTANCE_PROFILES_TEMPLATE)
        return template.render(instance_profiles=profiles)

    def upload_server_certificate(self):
        cert_name = self._get_param('ServerCertificateName')
        cert_body = self._get_param('CertificateBody')
        path = self._get_param('Path')
        private_key = self._get_param('PrivateKey')
        cert_chain = self._get_param('CertificateName')

        cert = iam_backend.upload_server_cert(cert_name, cert_body, private_key, cert_chain=cert_chain, path=path)
        template = Template(UPLOAD_CERT_TEMPLATE)
        return template.render(certificate=cert)

    def list_server_certificates(self, marker=None):
        certs = iam_backend.get_all_server_certs(marker=marker)
        template = Template(LIST_SERVER_CERTIFICATES_TEMPLATE)
        return template.render(server_certificates=certs)

    def get_server_certificate(self):
        cert_name = self._get_param('ServerCertificateName')
        cert = iam_backend.get_server_certificate(cert_name)
        template = Template(GET_SERVER_CERTIFICATE_TEMPLATE)
        return template.render(certificate=cert)


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

LIST_INSTANCE_PROFILES_TEMPLATE = """<ListInstanceProfilesResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ListInstanceProfilesResult>
    <IsTruncated>false</IsTruncated>
    <InstanceProfiles>
      {% for instance in instance_profiles %}
      <member>
        <Id>{{ instance.id }}</Id>
        <Roles/>
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

