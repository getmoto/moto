import time
import json
import datetime

from typing import Any, Dict, List, Tuple, Optional

from moto.core import BaseBackend, BackendDict, BaseModel
from moto.moto_api._internal import mock_random
from .exceptions import (
    SecretNotFoundException,
    SecretHasNoValueException,
    InvalidParameterException,
    ResourceExistsException,
    ResourceNotFoundException,
    SecretStageVersionMismatchException,
    InvalidRequestException,
    ClientError,
)
from .utils import random_password, secret_arn, get_secret_name_from_partial_arn
from .list_secrets.filters import (
    filter_all,
    tag_key,
    tag_value,
    description_filter,
    name_filter,
)


_filter_functions = {
    "all": filter_all,
    "name": name_filter,
    "description": description_filter,
    "tag-key": tag_key,
    "tag-value": tag_value,
}


def filter_keys() -> List[str]:
    return list(_filter_functions.keys())


def _matches(secret: "FakeSecret", filters: List[Dict[str, Any]]) -> bool:
    is_match = True

    for f in filters:
        # Filter names are pre-validated in the resource layer
        filter_function = _filter_functions.get(f["Key"])
        is_match = is_match and filter_function(secret, f["Values"])  # type: ignore

    return is_match


class SecretsManager(BaseModel):
    def __init__(self, region_name: str):
        self.region = region_name


class FakeSecret:
    def __init__(
        self,
        account_id: str,
        region_name: str,
        secret_id: str,
        secret_version: Dict[str, Any],
        version_id: str,
        secret_string: Optional[str] = None,
        secret_binary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        kms_key_id: Optional[str] = None,
        version_stages: Optional[List[str]] = None,
        last_changed_date: Optional[int] = None,
        created_date: Optional[int] = None,
    ):
        self.secret_id = secret_id
        self.name = secret_id
        self.arn = secret_arn(account_id, region_name, secret_id)
        self.secret_string = secret_string
        self.secret_binary = secret_binary
        self.description = description
        self.tags = tags or []
        self.kms_key_id = kms_key_id
        self.version_stages = version_stages
        self.last_changed_date = last_changed_date
        self.created_date = created_date
        # We should only return Rotation details after it's been requested
        self.rotation_requested = False
        self.rotation_enabled = False
        self.rotation_lambda_arn = ""
        self.auto_rotate_after_days = 0
        self.deleted_date: Optional[float] = None
        self.policy: Optional[str] = None
        self.next_rotation_date: Optional[int] = None
        self.last_rotation_date: Optional[int] = None

        self.versions: Dict[str, Dict[str, Any]] = {}
        if secret_string or secret_binary:
            self.versions = {version_id: secret_version}
            self.set_default_version_id(version_id)
        else:
            self.set_default_version_id(None)

    def update(
        self,
        description: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        kms_key_id: Optional[str] = None,
        last_changed_date: Optional[int] = None,
    ) -> None:
        self.description = description
        self.tags = tags or []
        if last_changed_date is not None:
            self.last_changed_date = last_changed_date

        if kms_key_id is not None:
            self.kms_key_id = kms_key_id

    def set_default_version_id(self, version_id: Optional[str]) -> None:
        self.default_version_id = version_id

    def reset_default_version(
        self, secret_version: Dict[str, Any], version_id: str
    ) -> None:
        # remove all old AWSPREVIOUS stages
        for old_version in self.versions.values():
            if "AWSPREVIOUS" in old_version["version_stages"]:
                old_version["version_stages"].remove("AWSPREVIOUS")

        # set old AWSCURRENT secret to AWSPREVIOUS
        previous_current_version_id = self.default_version_id
        self.versions[previous_current_version_id]["version_stages"] = ["AWSPREVIOUS"]  # type: ignore

        self.versions[version_id] = secret_version
        self.default_version_id = version_id

    def remove_version_stages_from_old_versions(
        self, version_stages: List[str]
    ) -> None:
        for version_stage in version_stages:
            for old_version in self.versions.values():
                if version_stage in old_version["version_stages"]:
                    old_version["version_stages"].remove(version_stage)

    def delete(self, deleted_date: float) -> None:
        self.deleted_date = deleted_date

    def restore(self) -> None:
        self.deleted_date = None

    def is_deleted(self) -> bool:
        return self.deleted_date is not None

    def to_short_dict(
        self,
        include_version_stages: bool = False,
        version_id: Optional[str] = None,
        include_version_id: bool = True,
    ) -> str:
        if not version_id:
            version_id = self.default_version_id
        dct = {
            "ARN": self.arn,
            "Name": self.name,
        }
        if include_version_id and version_id:
            dct["VersionId"] = version_id
        if version_id and include_version_stages:
            dct["VersionStages"] = self.versions[version_id]["version_stages"]
        return json.dumps(dct)

    def to_dict(self) -> Dict[str, Any]:
        version_id_to_stages = self._form_version_ids_to_stages()

        dct: Dict[str, Any] = {
            "ARN": self.arn,
            "Name": self.name,
            "KmsKeyId": self.kms_key_id,
            "LastChangedDate": self.last_changed_date,
            "LastAccessedDate": None,
            "NextRotationDate": self.next_rotation_date,
            "DeletedDate": self.deleted_date,
            "CreatedDate": self.created_date,
        }
        if self.tags:
            dct["Tags"] = self.tags
        if self.description:
            dct["Description"] = self.description
        if self.versions:
            dct.update(
                {
                    # Key used by describe_secret
                    "VersionIdsToStages": version_id_to_stages,
                    # Key used by list_secrets
                    "SecretVersionsToStages": version_id_to_stages,
                }
            )
        if self.rotation_requested:
            dct.update(
                {
                    "RotationEnabled": self.rotation_enabled,
                    "RotationLambdaARN": self.rotation_lambda_arn,
                    "RotationRules": {
                        "AutomaticallyAfterDays": self.auto_rotate_after_days
                    },
                    "LastRotatedDate": self.last_rotation_date,
                }
            )
        return dct

    def _form_version_ids_to_stages(self) -> Dict[str, str]:
        version_id_to_stages = {}
        for key, value in self.versions.items():
            version_id_to_stages[key] = value["version_stages"]

        return version_id_to_stages


class SecretsStore(Dict[str, FakeSecret]):
    # Parameters to this dictionary can be three possible values:
    # names, full ARNs, and partial ARNs
    # Every retrieval method should check which type of input it receives

    def __setitem__(self, key: str, value: FakeSecret) -> None:
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> FakeSecret:
        for secret in dict.values(self):
            if secret.arn == key or secret.name == key:
                return secret
        name = get_secret_name_from_partial_arn(key)
        return super().__getitem__(name)

    def __contains__(self, key: str) -> bool:  # type: ignore
        for secret in dict.values(self):
            if secret.arn == key or secret.name == key:
                return True
        name = get_secret_name_from_partial_arn(key)
        return dict.__contains__(self, name)  # type: ignore

    def get(self, key: str) -> Optional[FakeSecret]:  # type: ignore
        for secret in dict.values(self):
            if secret.arn == key or secret.name == key:
                return secret
        name = get_secret_name_from_partial_arn(key)
        return super().get(name)

    def pop(self, key: str) -> Optional[FakeSecret]:  # type: ignore
        for secret in dict.values(self):
            if secret.arn == key or secret.name == key:
                key = secret.name
        name = get_secret_name_from_partial_arn(key)
        return super().pop(name, None)


class SecretsManagerBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.secrets = SecretsStore()

    @staticmethod
    def default_vpc_endpoint_service(
        service_region: str, zones: List[str]
    ) -> List[Dict[str, str]]:
        """Default VPC endpoint services."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "secretsmanager"
        )

    def _is_valid_identifier(self, identifier: str) -> bool:
        return identifier in self.secrets

    def _unix_time_secs(self, dt: datetime.datetime) -> float:
        epoch = datetime.datetime.utcfromtimestamp(0)
        return (dt - epoch).total_seconds()

    def _client_request_token_validator(self, client_request_token: str) -> None:
        token_length = len(client_request_token)
        if token_length < 32 or token_length > 64:
            msg = "ClientRequestToken must be 32-64 characters long."
            raise InvalidParameterException(msg)

    def _from_client_request_token(self, client_request_token: Optional[str]) -> str:
        if client_request_token:
            self._client_request_token_validator(client_request_token)
            return client_request_token
        else:
            return str(mock_random.uuid4())

    def cancel_rotate_secret(self, secret_id: str) -> str:
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        if secret.is_deleted():
            raise InvalidRequestException(
                "You tried to perform the operation on a secret that's currently marked deleted."
            )

        if not secret.rotation_lambda_arn:
            # This response doesn't make much sense for  `CancelRotateSecret`, but this is what AWS has documented ...
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_CancelRotateSecret.html
            raise InvalidRequestException(
                (
                    "You tried to enable rotation on a secret that doesn't already have a Lambda function ARN configured"
                    "and you didn't include such an ARN as a parameter in this call."
                )
            )

        secret.rotation_enabled = False
        return secret.to_short_dict()

    def get_secret_value(
        self, secret_id: str, version_id: str, version_stage: str
    ) -> Dict[str, Any]:
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        if version_id and version_stage:
            versions_dict = self.secrets[secret_id].versions
            if (
                version_id in versions_dict
                and version_stage not in versions_dict[version_id]["version_stages"]
            ):
                raise SecretStageVersionMismatchException()

        version_id_provided = version_id is not None
        if not version_id and version_stage:
            # set version_id to match version_stage
            versions_dict = self.secrets[secret_id].versions
            for ver_id, ver_val in versions_dict.items():
                if version_stage in ver_val["version_stages"]:
                    version_id = ver_id
                    break
            if not version_id:
                raise SecretNotFoundException()

        # TODO check this part
        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the GetSecretValue operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        secret = self.secrets[secret_id]
        version_id = version_id or secret.default_version_id or "AWSCURRENT"

        secret_version = secret.versions.get(version_id)
        if not secret_version:
            _type = "staging label" if not version_id_provided else "VersionId"
            raise ResourceNotFoundException(
                f"Secrets Manager can't find the specified secret value for {_type}: {version_id}"
            )

        response_data = {
            "ARN": secret.arn,
            "Name": secret.name,
            "VersionId": secret_version["version_id"],
            "VersionStages": secret_version["version_stages"],
            "CreatedDate": secret_version["createdate"],
        }

        if "secret_string" in secret_version:
            response_data["SecretString"] = secret_version["secret_string"]

        if "secret_binary" in secret_version:
            response_data["SecretBinary"] = secret_version["secret_binary"]

        if (
            "secret_string" not in secret_version
            and "secret_binary" not in secret_version
        ):
            raise SecretHasNoValueException(version_stage or "AWSCURRENT")

        return response_data

    def update_secret(
        self,
        secret_id: str,
        secret_string: Optional[str] = None,
        secret_binary: Optional[str] = None,
        client_request_token: Optional[str] = None,
        kms_key_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:

        # error if secret does not exist
        if secret_id not in self.secrets:
            raise SecretNotFoundException()

        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the UpdateSecret operation: "
                "You can't perform this operation on the secret because it was marked for deletion."
            )

        secret = self.secrets[secret_id]
        tags = secret.tags
        description = description or secret.description

        secret, new_version = self._add_secret(
            secret_id,
            secret_string=secret_string,
            secret_binary=secret_binary,
            description=description,
            version_id=client_request_token,
            tags=tags,
            kms_key_id=kms_key_id,
        )

        return secret.to_short_dict(include_version_id=new_version)

    def create_secret(
        self,
        name: str,
        secret_string: Optional[str] = None,
        secret_binary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        kms_key_id: Optional[str] = None,
        client_request_token: Optional[str] = None,
    ) -> str:

        # error if secret exists
        if name in self.secrets.keys():
            raise ResourceExistsException(
                "A resource with the ID you requested already exists."
            )

        secret, new_version = self._add_secret(
            name,
            secret_string=secret_string,
            secret_binary=secret_binary,
            description=description,
            tags=tags,
            kms_key_id=kms_key_id,
            version_id=client_request_token,
        )

        return secret.to_short_dict(include_version_id=new_version)

    def _add_secret(
        self,
        secret_id: str,
        secret_string: Optional[str] = None,
        secret_binary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        kms_key_id: Optional[str] = None,
        version_id: Optional[str] = None,
        version_stages: Optional[List[str]] = None,
    ) -> Tuple[FakeSecret, bool]:

        if version_stages is None:
            version_stages = ["AWSCURRENT"]

        version_id = self._from_client_request_token(version_id)

        secret_version = {
            "createdate": int(time.time()),
            "version_id": version_id,
            "version_stages": version_stages,
        }
        if secret_string is not None:
            secret_version["secret_string"] = secret_string

        if secret_binary is not None:
            secret_version["secret_binary"] = secret_binary

        new_version = secret_string is not None or secret_binary is not None

        update_time = int(time.time())
        if secret_id in self.secrets:
            secret = self.secrets[secret_id]

            secret.update(description, tags, kms_key_id, last_changed_date=update_time)

            if new_version:
                if "AWSCURRENT" in version_stages:
                    secret.reset_default_version(secret_version, version_id)
                else:
                    secret.remove_version_stages_from_old_versions(version_stages)
                    secret.versions[version_id] = secret_version
        else:
            secret = FakeSecret(
                account_id=self.account_id,
                region_name=self.region_name,
                secret_id=secret_id,
                secret_string=secret_string,
                secret_binary=secret_binary,
                description=description,
                tags=tags,
                kms_key_id=kms_key_id,
                last_changed_date=update_time,
                created_date=update_time,
                version_id=version_id,
                secret_version=secret_version,
            )
            self.secrets[secret_id] = secret

        return secret, new_version

    def put_secret_value(
        self,
        secret_id: str,
        secret_string: str,
        secret_binary: str,
        client_request_token: str,
        version_stages: List[str],
    ) -> str:

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()
        else:
            secret = self.secrets[secret_id]
            tags = secret.tags
            description = secret.description

        version_id = self._from_client_request_token(client_request_token)

        secret, _ = self._add_secret(
            secret_id,
            secret_string,
            secret_binary,
            version_id=version_id,
            description=description,
            tags=tags,
            version_stages=version_stages,
        )

        return secret.to_short_dict(include_version_stages=True, version_id=version_id)

    def describe_secret(self, secret_id: str) -> Dict[str, Any]:
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]

        return secret.to_dict()

    def rotate_secret(
        self,
        secret_id: str,
        client_request_token: Optional[str] = None,
        rotation_lambda_arn: Optional[str] = None,
        rotation_rules: Optional[Dict[str, Any]] = None,
    ) -> str:
        rotation_days = "AutomaticallyAfterDays"

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the RotateSecret operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        if rotation_lambda_arn:
            if len(rotation_lambda_arn) > 2048:
                msg = "RotationLambdaARN " "must <= 2048 characters long."
                raise InvalidParameterException(msg)

        if rotation_rules:
            if rotation_days in rotation_rules:
                rotation_period = rotation_rules[rotation_days]
                if rotation_period < 1 or rotation_period > 1000:
                    msg = (
                        "RotationRules.AutomaticallyAfterDays " "must be within 1-1000."
                    )
                    raise InvalidParameterException(msg)

                self.secrets[secret_id].next_rotation_date = int(time.time()) + (
                    int(rotation_period) * 86400
                )

        secret = self.secrets[secret_id]

        # The rotation function must end with the versions of the secret in
        # one of two states:
        #
        #  - The AWSPENDING and AWSCURRENT staging labels are attached to the
        #    same version of the secret, or
        #  - The AWSPENDING staging label is not attached to any version of the secret.
        #
        # If the AWSPENDING staging label is present but not attached to the same
        # version as AWSCURRENT then any later invocation of RotateSecret assumes
        # that a previous rotation request is still in progress and returns an error.
        try:
            version = next(
                version
                for version in secret.versions.values()
                if "AWSPENDING" in version["version_stages"]
            )
            if "AWSCURRENT" in version["version_stages"]:
                msg = "Previous rotation request is still in progress."
                raise InvalidRequestException(msg)

        except StopIteration:
            # Pending is not present in any version
            pass

        if secret.versions:
            old_secret_version = secret.versions[secret.default_version_id]  # type: ignore

            if client_request_token:
                self._client_request_token_validator(client_request_token)
                new_version_id = client_request_token
            else:
                new_version_id = str(mock_random.uuid4())

            # We add the new secret version as "pending". The previous version remains
            # as "current" for now. Once we've passed the new secret through the lambda
            # rotation function (if provided) we can then update the status to "current".
            old_secret_version_secret_string = (
                old_secret_version["secret_string"]
                if "secret_string" in old_secret_version
                else None
            )
            self._add_secret(
                secret_id,
                old_secret_version_secret_string,
                description=secret.description,
                tags=secret.tags,
                version_id=new_version_id,
                version_stages=["AWSPENDING"],
            )

        secret.rotation_requested = True
        secret.rotation_lambda_arn = rotation_lambda_arn or ""
        if rotation_rules:
            secret.auto_rotate_after_days = rotation_rules.get(rotation_days, 0)
        if secret.auto_rotate_after_days > 0:
            secret.rotation_enabled = True

        # Begin the rotation process for the given secret by invoking the lambda function.
        if secret.rotation_lambda_arn:
            from moto.awslambda.models import lambda_backends

            lambda_backend = lambda_backends[self.account_id][self.region_name]

            request_headers: Dict[str, Any] = {}
            response_headers: Dict[str, Any] = {}

            try:
                func = lambda_backend.get_function(secret.rotation_lambda_arn)
            except Exception:
                msg = f"Resource not found for ARN '{secret.rotation_lambda_arn}'."
                raise ResourceNotFoundException(msg)

            for step in ["create", "set", "test", "finish"]:
                func.invoke(
                    json.dumps(
                        {
                            "Step": step + "Secret",
                            "SecretId": secret.name,
                            "ClientRequestToken": new_version_id,
                        }
                    ),
                    request_headers,
                    response_headers,
                )

            secret.set_default_version_id(new_version_id)
        elif secret.versions:
            # AWS will always require a Lambda ARN
            # without that, Moto can still apply the 'AWSCURRENT'-label
            # This only makes sense if we have a version
            secret.reset_default_version(
                secret.versions[new_version_id], new_version_id
            )
            secret.versions[new_version_id]["version_stages"] = ["AWSCURRENT"]

        self.secrets[secret_id].last_rotation_date = int(time.time())
        return secret.to_short_dict()

    def get_random_password(
        self,
        password_length: int,
        exclude_characters: str,
        exclude_numbers: bool,
        exclude_punctuation: bool,
        exclude_uppercase: bool,
        exclude_lowercase: bool,
        include_space: bool,
        require_each_included_type: bool,
    ) -> str:
        # password size must have value less than or equal to 4096
        if password_length > 4096:
            raise ClientError(
                f"ClientError: An error occurred (ValidationException) \
                when calling the GetRandomPassword operation: 1 validation error detected: Value '{password_length}' at 'passwordLength' \
                failed to satisfy constraint: Member must have value less than or equal to 4096"
            )
        if password_length < 4:
            raise InvalidParameterException(
                "InvalidParameterException: An error occurred (InvalidParameterException) \
                when calling the GetRandomPassword operation: Password length is too short based on the required types."
            )

        return json.dumps(
            {
                "RandomPassword": random_password(
                    password_length,
                    exclude_characters,
                    exclude_numbers,
                    exclude_punctuation,
                    exclude_uppercase,
                    exclude_lowercase,
                    include_space,
                    require_each_included_type,
                )
            }
        )

    def list_secret_version_ids(self, secret_id: str) -> str:
        secret = self.secrets[secret_id]

        version_list = []
        for version_id, version in secret.versions.items():
            version_list.append(
                {
                    "CreatedDate": int(time.time()),
                    "LastAccessedDate": int(time.time()),
                    "VersionId": version_id,
                    "VersionStages": version["version_stages"],
                }
            )

        return json.dumps(
            {
                "ARN": secret.secret_id,
                "Name": secret.name,
                "NextToken": "",
                "Versions": version_list,
            }
        )

    def list_secrets(
        self,
        filters: List[Dict[str, Any]],
        max_results: int = 100,
        next_token: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        secret_list = []
        for secret in self.secrets.values():
            if _matches(secret, filters):
                secret_list.append(secret.to_dict())

        starting_point = int(next_token or 0)
        ending_point = starting_point + int(max_results or 100)
        secret_page = secret_list[starting_point:ending_point]
        new_next_token = str(ending_point) if ending_point < len(secret_list) else None

        return secret_page, new_next_token

    def delete_secret(
        self,
        secret_id: str,
        recovery_window_in_days: int,
        force_delete_without_recovery: bool,
    ) -> Tuple[str, str, float]:

        if recovery_window_in_days is not None and (
            recovery_window_in_days < 7 or recovery_window_in_days > 30
        ):
            raise InvalidParameterException(
                "An error occurred (InvalidParameterException) when calling the DeleteSecret operation: The \
                RecoveryWindowInDays value must be between 7 and 30 days (inclusive)."
            )

        if recovery_window_in_days and force_delete_without_recovery:
            raise InvalidParameterException(
                "An error occurred (InvalidParameterException) when calling the DeleteSecret operation: You can't \
                use ForceDeleteWithoutRecovery in conjunction with RecoveryWindowInDays."
            )

        if not self._is_valid_identifier(secret_id):
            if not force_delete_without_recovery:
                raise SecretNotFoundException()
            else:
                arn = secret_arn(self.account_id, self.region_name, secret_id=secret_id)
                name = secret_id
                deletion_date = datetime.datetime.utcnow()
                return arn, name, self._unix_time_secs(deletion_date)
        else:
            if self.secrets[secret_id].is_deleted():
                raise InvalidRequestException(
                    "An error occurred (InvalidRequestException) when calling the DeleteSecret operation: You tried to \
                    perform the operation on a secret that's currently marked deleted."
                )

            deletion_date = datetime.datetime.utcnow()

            if force_delete_without_recovery:
                secret = self.secrets.pop(secret_id)
            else:
                deletion_date += datetime.timedelta(days=recovery_window_in_days or 30)
                self.secrets[secret_id].delete(self._unix_time_secs(deletion_date))
                secret = self.secrets.get(secret_id)

            if not secret:
                raise SecretNotFoundException()

            arn = secret.arn
            name = secret.name

            return arn, name, self._unix_time_secs(deletion_date)

    def restore_secret(self, secret_id: str) -> Tuple[str, str]:

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        secret.restore()

        return secret.arn, secret.name

    def tag_resource(self, secret_id: str, tags: List[Dict[str, str]]) -> None:

        if secret_id not in self.secrets:
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        old_tags = secret.tags

        for tag in tags:
            existing_key_name = next(
                (
                    old_key
                    for old_key in old_tags
                    if old_key.get("Key") == tag.get("Key")
                ),
                None,
            )
            if existing_key_name:
                old_tags.remove(existing_key_name)
            old_tags.append(tag)

    def untag_resource(self, secret_id: str, tag_keys: List[str]) -> None:

        if secret_id not in self.secrets:
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        tags = secret.tags

        for tag in tags:
            if tag["Key"] in tag_keys:
                tags.remove(tag)

    def update_secret_version_stage(
        self,
        secret_id: str,
        version_stage: str,
        remove_from_version_id: str,
        move_to_version_id: str,
    ) -> Tuple[str, str]:
        if secret_id not in self.secrets:
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]

        if remove_from_version_id:
            if remove_from_version_id not in secret.versions:
                raise InvalidParameterException(
                    f"Not a valid version: {remove_from_version_id}"
                )

            stages = secret.versions[remove_from_version_id]["version_stages"]
            if version_stage not in stages:
                raise InvalidParameterException(
                    f"Version stage {version_stage} not found in version {remove_from_version_id}"
                )

            stages.remove(version_stage)

        if move_to_version_id:
            if move_to_version_id not in secret.versions:
                raise InvalidParameterException(
                    f"Not a valid version: {move_to_version_id}"
                )

            stages = secret.versions[move_to_version_id]["version_stages"]
            stages.append(version_stage)

        if version_stage == "AWSCURRENT":
            if remove_from_version_id:
                # Whenever you move AWSCURRENT, Secrets Manager automatically
                # moves the label AWSPREVIOUS to the version that AWSCURRENT
                # was removed from.
                secret.versions[remove_from_version_id]["version_stages"].append(
                    "AWSPREVIOUS"
                )

            if move_to_version_id:
                stages = secret.versions[move_to_version_id]["version_stages"]
                if "AWSPREVIOUS" in stages:
                    stages.remove("AWSPREVIOUS")

        return secret.arn, secret.name

    def put_resource_policy(self, secret_id: str, policy: str) -> Tuple[str, str]:
        """
        The BlockPublicPolicy-parameter is not yet implemented
        """
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        secret.policy = policy
        return secret.arn, secret.name

    def get_resource_policy(self, secret_id: str) -> str:
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        resp = {
            "ARN": secret.arn,
            "Name": secret.name,
        }
        if secret.policy is not None:
            resp["ResourcePolicy"] = secret.policy
        return json.dumps(resp)

    def delete_resource_policy(self, secret_id: str) -> Tuple[str, str]:
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        secret.policy = None
        return secret.arn, secret.name


secretsmanager_backends = BackendDict(SecretsManagerBackend, "secretsmanager")
