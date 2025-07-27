from moto.core.responses import ActionResult, BaseResponse

from .exceptions import STSValidationError
from .models import STSBackend, sts_backends

MAX_FEDERATION_TOKEN_POLICY_LENGTH = 2048


class TokenResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="sts")

    @property
    def backend(self) -> STSBackend:
        return sts_backends[self.current_account][self.partition]

    def _determine_resource(self) -> str:
        if "AssumeRole" in self.querystring.get("Action", []):
            return self.querystring.get("RoleArn")[0]  # type: ignore[index]
        return "*"

    def get_session_token(self) -> ActionResult:
        duration = int(self.querystring.get("DurationSeconds", [43200])[0])
        token = self.backend.get_session_token(duration=duration)
        result = {
            "Credentials": {
                "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY",
                "SessionToken": "AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE",
                "Expiration": token.expiration,
            }
        }
        return ActionResult(result)

    def get_federation_token(self) -> ActionResult:
        duration = int(self.querystring.get("DurationSeconds", [43200])[0])
        policy = self.querystring.get("Policy", [None])[0]

        if policy is not None and len(policy) > MAX_FEDERATION_TOKEN_POLICY_LENGTH:
            raise STSValidationError(
                "1 validation error detected: Value "
                '\'{"Version": "2012-10-17", "Statement": [...]}\' '
                "at 'policy' failed to satisfy constraint: Member must have length less than or "
                f" equal to {MAX_FEDERATION_TOKEN_POLICY_LENGTH}"
            )

        name = self.querystring.get("Name")[0]  # type: ignore
        token = self.backend.get_federation_token(duration=duration, name=name)
        result = {
            "Credentials": {
                "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY",
                "SessionToken": "AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA==",
                "Expiration": token.expiration,
            },
            "FederatedUser": {
                "FederatedUserId": f"{self.current_account}:{token.name}",
                "Arn": f"arn:{self.partition}:sts::{self.current_account}:federated-user/{token.name}",
            },
            "PackedPolicySize": 6,
        }
        return ActionResult(result)

    def assume_role(self) -> ActionResult:
        role_session_name = self.querystring.get("RoleSessionName")[0]  # type: ignore
        role_arn = self.querystring.get("RoleArn")[0]  # type: ignore

        policy = self.querystring.get("Policy", [None])[0]
        duration = int(self.querystring.get("DurationSeconds", [3600])[0])
        external_id = self.querystring.get("ExternalId", [None])[0]

        role = self.backend.assume_role(
            region_name=self.region,
            role_session_name=role_session_name,
            role_arn=role_arn,
            policy=policy,
            duration=duration,
            external_id=external_id,
        )
        result = {
            "Credentials": role,
            "AssumedRoleUser": {
                "AssumedRoleId": role.user_id,
                "Arn": role.arn,
            },
            "PackedPolicySize": 6,
        }
        return ActionResult(result)

    def assume_role_with_web_identity(self) -> ActionResult:
        role_session_name = self.querystring.get("RoleSessionName")[0]  # type: ignore
        role_arn = self.querystring.get("RoleArn")[0]  # type: ignore

        policy = self.querystring.get("Policy", [None])[0]
        duration = int(self.querystring.get("DurationSeconds", [3600])[0])
        external_id = self.querystring.get("ExternalId", [None])[0]

        role = self.backend.assume_role_with_web_identity(
            region_name=self.region,
            role_session_name=role_session_name,
            role_arn=role_arn,
            policy=policy,
            duration=duration,
            external_id=external_id,
        )
        result = {
            "Credentials": role,
            "AssumedRoleUser": {
                "AssumedRoleId": f"ARO123EXAMPLE123:{role.session_name}",
                "Arn": role.arn,
            },
            "PackedPolicySize": 6,
        }
        return ActionResult(result)

    def assume_role_with_saml(self) -> ActionResult:
        role_arn = self.querystring.get("RoleArn")[0]  # type: ignore
        principal_arn = self.querystring.get("PrincipalArn")[0]  # type: ignore
        saml_assertion = self.querystring.get("SAMLAssertion")[0]  # type: ignore

        role = self.backend.assume_role_with_saml(
            role_arn=role_arn,
            principal_arn=principal_arn,
            saml_assertion=saml_assertion,
        )
        result = {
            "Credentials": role,
            "AssumedRoleUser": {
                "AssumedRoleId": role.user_id,
                "Arn": role.arn,
            },
            "PackedPolicySize": 123,
            "Subject": role.user_id,
            "SubjectType": "persistent",
            "Issuer": "http://localhost:3000/",
            "Audience": "https://signin.aws.amazon.com/saml",
            "NameQualifier": "B64EncodedStringOfHashOfIssuerAccountIdAndUserId=",
        }
        return ActionResult(result)

    def get_caller_identity(self) -> ActionResult:
        access_key_id = self.get_access_key()
        user_id, arn, account_id = self.backend.get_caller_identity(
            access_key_id, self.region
        )
        result = {
            "UserId": user_id,
            "Account": account_id,
            "Arn": arn,
        }
        return ActionResult(result)
