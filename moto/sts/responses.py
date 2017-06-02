from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from .models import sts_backend


class TokenResponse(BaseResponse):

    def get_session_token(self):
        duration = int(self.querystring.get('DurationSeconds', [43200])[0])
        token = sts_backend.get_session_token(duration=duration)
        template = self.response_template(GET_SESSION_TOKEN_RESPONSE)
        return template.render(token=token)

    def get_federation_token(self):
        duration = int(self.querystring.get('DurationSeconds', [43200])[0])
        policy = self.querystring.get('Policy', [None])[0]
        name = self.querystring.get('Name')[0]
        token = sts_backend.get_federation_token(
            duration=duration, name=name, policy=policy)
        template = self.response_template(GET_FEDERATION_TOKEN_RESPONSE)
        return template.render(token=token)

    def assume_role(self):
        role_session_name = self.querystring.get('RoleSessionName')[0]
        role_arn = self.querystring.get('RoleArn')[0]

        policy = self.querystring.get('Policy', [None])[0]
        duration = int(self.querystring.get('DurationSeconds', [3600])[0])
        external_id = self.querystring.get('ExternalId', [None])[0]

        role = sts_backend.assume_role(
            role_session_name=role_session_name,
            role_arn=role_arn,
            policy=policy,
            duration=duration,
            external_id=external_id,
        )
        template = self.response_template(ASSUME_ROLE_RESPONSE)
        return template.render(role=role)

    def get_caller_identity(self):
        template = self.response_template(GET_CALLER_IDENTITY_RESPONSE)
        return template.render()


GET_SESSION_TOKEN_RESPONSE = """<GetSessionTokenResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetSessionTokenResult>
    <Credentials>
      <SessionToken>AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE</SessionToken>
      <SecretAccessKey>wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY</SecretAccessKey>
      <Expiration>{{ token.expiration_ISO8601 }}</Expiration>
      <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
    </Credentials>
  </GetSessionTokenResult>
  <ResponseMetadata>
    <RequestId>58c5dbae-abef-11e0-8cfe-09039844ac7d</RequestId>
  </ResponseMetadata>
</GetSessionTokenResponse>"""


GET_FEDERATION_TOKEN_RESPONSE = """<GetFederationTokenResponse xmlns="https://sts.amazonaws.com/doc/
2011-06-15/">
  <GetFederationTokenResult>
    <Credentials>
      <SessionToken>AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA==</SessionToken>
      <SecretAccessKey>wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY</SecretAccessKey>
      <Expiration>{{ token.expiration_ISO8601 }}</Expiration>
      <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
    </Credentials>
    <FederatedUser>
      <Arn>arn:aws:sts::123456789012:federated-user/{{ token.name }}</Arn>
      <FederatedUserId>123456789012:{{ token.name }}</FederatedUserId>
    </FederatedUser>
    <PackedPolicySize>6</PackedPolicySize>
  </GetFederationTokenResult>
  <ResponseMetadata>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
  </ResponseMetadata>
</GetFederationTokenResponse>"""


ASSUME_ROLE_RESPONSE = """<AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/
2011-06-15/">
  <AssumeRoleResult>
    <Credentials>
      <SessionToken>BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE</SessionToken>
      <SecretAccessKey>aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY</SecretAccessKey>
      <Expiration>{{ role.expiration_ISO8601 }}</Expiration>
      <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
    </Credentials>
    <AssumedRoleUser>
      <Arn>{{ role.arn }}</Arn>
      <AssumedRoleId>ARO123EXAMPLE123:{{ role.session_name }}</AssumedRoleId>
    </AssumedRoleUser>
    <PackedPolicySize>6</PackedPolicySize>
  </AssumeRoleResult>
  <ResponseMetadata>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
  </ResponseMetadata>
</AssumeRoleResponse>"""

GET_CALLER_IDENTITY_RESPONSE = """<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:sts::123456789012:user/moto</Arn>
    <UserId>AKIAIOSFODNN7EXAMPLE</UserId>
    <Account>123456789012</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
  </ResponseMetadata>
</GetCallerIdentityResponse>
"""
