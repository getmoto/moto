from moto.core.responses import BaseResponse
from .exceptions import PasswordTooShort, PasswordRequired
from .models import elasticache_backends


class ElastiCacheResponse(BaseResponse):
    """Handler for ElastiCache requests and responses."""

    @property
    def elasticache_backend(self):
        """Return backend instance specific for this region."""
        return elasticache_backends[self.region]

    def create_user(self):
        params = self._get_params()
        user_id = params.get("UserId")
        user_name = params.get("UserName")
        engine = params.get("Engine")
        passwords = params.get("Passwords", [])
        no_password_required = self._get_bool_param("NoPasswordRequired", False)
        password_required = not no_password_required
        if password_required and not passwords:
            raise PasswordRequired
        if any([len(p) < 16 for p in passwords]):
            raise PasswordTooShort
        access_string = params.get("AccessString")
        user = self.elasticache_backend.create_user(
            user_id=user_id,
            user_name=user_name,
            engine=engine,
            passwords=passwords,
            access_string=access_string,
            no_password_required=no_password_required,
        )
        template = self.response_template(CREATE_USER_TEMPLATE)
        return template.render(user=user)

    def delete_user(self):
        params = self._get_params()
        user_id = params.get("UserId")
        user = self.elasticache_backend.delete_user(user_id=user_id)
        template = self.response_template(DELETE_USER_TEMPLATE)
        return template.render(user=user)

    def describe_users(self):
        params = self._get_params()
        user_id = params.get("UserId")
        users = self.elasticache_backend.describe_users(user_id=user_id)
        template = self.response_template(DESCRIBE_USERS_TEMPLATE)
        return template.render(users=users)


USER_TEMPLATE = """<UserId>{{ user.id }}</UserId>
    <UserName>{{ user.name }}</UserName>
    <Status>{{ user.status }}</Status>
    <Engine>{{ user.engine }}</Engine>
    <MinimumEngineVersion>{{ user.minimum_engine_version }}</MinimumEngineVersion>
    <AccessString>{{ user.access_string }}</AccessString>
    <UserGroupIds>
{% for usergroupid in user.usergroupids %}
      <member>{{ usergroupid }}</member>
{% endfor %}
    </UserGroupIds>
    <Authentication>
      {% if user.no_password_required %}
      <Type>no-password</Type>
      {% else %}
      <Type>password</Type>
      <PasswordCount>{{ user.passwords|length }}</PasswordCount>
      {% endif %}
    </Authentication>
    <ARN>{{ user.arn }}</ARN>"""


CREATE_USER_TEMPLATE = (
    """<CreateUserResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <CreateUserResult>
    """
    + USER_TEMPLATE
    + """
  </CreateUserResult>
</CreateUserResponse>"""
)

DELETE_USER_TEMPLATE = (
    """<DeleteUserResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <DeleteUserResult>
    """
    + USER_TEMPLATE
    + """
  </DeleteUserResult>
</DeleteUserResponse>"""
)

DESCRIBE_USERS_TEMPLATE = (
    """<DescribeUsersResponse xmlns="http://elasticache.amazonaws.com/doc/2015-02-02/">
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <DescribeUsersResult>
    <Users>
{% for user in users %}
      <member>
        """
    + USER_TEMPLATE
    + """
      </member>
{% endfor %}
    </Users>
    <Marker></Marker>
  </DescribeUsersResult>
</DescribeUsersResponse>"""
)
