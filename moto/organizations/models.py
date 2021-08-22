from __future__ import unicode_literals

import datetime
import re
import json

from moto.core import BaseBackend, BaseModel, ACCOUNT_ID
from moto.core.exceptions import RESTError
from moto.core.utils import unix_time
from moto.organizations import utils
from moto.organizations.exceptions import (
    InvalidInputException,
    DuplicateOrganizationalUnitException,
    DuplicatePolicyException,
    AccountNotFoundException,
    ConstraintViolationException,
    AccountAlreadyRegisteredException,
    AWSOrganizationsNotInUseException,
    AccountNotRegisteredException,
    RootNotFoundException,
    PolicyTypeAlreadyEnabledException,
    PolicyTypeNotEnabledException,
    TargetNotFoundException,
)


class FakeOrganization(BaseModel):
    def __init__(self, feature_set):
        self.id = utils.make_random_org_id()
        self.root_id = utils.make_random_root_id()
        self.feature_set = feature_set
        self.master_account_id = utils.MASTER_ACCOUNT_ID
        self.master_account_email = utils.MASTER_ACCOUNT_EMAIL
        self.available_policy_types = [
            # TODO: verify if this should be enabled by default (breaks TF tests for CloudTrail)
            {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
        ]

    @property
    def arn(self):
        return utils.ORGANIZATION_ARN_FORMAT.format(self.master_account_id, self.id)

    @property
    def master_account_arn(self):
        return utils.MASTER_ACCOUNT_ARN_FORMAT.format(self.master_account_id, self.id)

    def describe(self):
        return {
            "Organization": {
                "Id": self.id,
                "Arn": self.arn,
                "FeatureSet": self.feature_set,
                "MasterAccountArn": self.master_account_arn,
                "MasterAccountId": self.master_account_id,
                "MasterAccountEmail": self.master_account_email,
                "AvailablePolicyTypes": self.available_policy_types,
            }
        }


class FakeAccount(BaseModel):
    def __init__(self, organization, **kwargs):
        self.type = "ACCOUNT"
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.create_account_status_id = utils.make_random_create_account_status_id()
        self.id = utils.make_random_account_id()
        self.name = kwargs["AccountName"]
        self.email = kwargs["Email"]
        self.create_time = datetime.datetime.utcnow()
        self.status = "ACTIVE"
        self.joined_method = "CREATED"
        self.parent_id = organization.root_id
        self.attached_policies = []
        self.tags = {tag["Key"]: tag["Value"] for tag in kwargs.get("Tags", [])}

    @property
    def arn(self):
        return utils.ACCOUNT_ARN_FORMAT.format(
            self.master_account_id, self.organization_id, self.id
        )

    @property
    def create_account_status(self):
        return {
            "CreateAccountStatus": {
                "Id": self.create_account_status_id,
                "AccountName": self.name,
                "State": "SUCCEEDED",
                "RequestedTimestamp": unix_time(self.create_time),
                "CompletedTimestamp": unix_time(self.create_time),
                "AccountId": self.id,
            }
        }

    def describe(self):
        return {
            "Id": self.id,
            "Arn": self.arn,
            "Email": self.email,
            "Name": self.name,
            "Status": self.status,
            "JoinedMethod": self.joined_method,
            "JoinedTimestamp": unix_time(self.create_time),
        }


class FakeOrganizationalUnit(BaseModel):
    def __init__(self, organization, **kwargs):
        self.type = "ORGANIZATIONAL_UNIT"
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.id = utils.make_random_ou_id(organization.root_id)
        self.name = kwargs.get("Name")
        self.parent_id = kwargs.get("ParentId")
        self._arn_format = utils.OU_ARN_FORMAT
        self.attached_policies = []
        self.tags = {tag["Key"]: tag["Value"] for tag in kwargs.get("Tags", [])}

    @property
    def arn(self):
        return self._arn_format.format(
            self.master_account_id, self.organization_id, self.id
        )

    def describe(self):
        return {
            "OrganizationalUnit": {"Id": self.id, "Arn": self.arn, "Name": self.name}
        }


class FakeRoot(FakeOrganizationalUnit):
    SUPPORTED_POLICY_TYPES = [
        "AISERVICES_OPT_OUT_POLICY",
        "BACKUP_POLICY",
        "SERVICE_CONTROL_POLICY",
        "TAG_POLICY",
    ]

    def __init__(self, organization, **kwargs):
        super(FakeRoot, self).__init__(organization, **kwargs)
        self.type = "ROOT"
        self.id = organization.root_id
        self.name = "Root"
        self.policy_types = [
            # TODO: verify if this should be enabled by default (breaks TF tests for CloudTrail)
            {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
        ]
        self._arn_format = utils.ROOT_ARN_FORMAT
        self.attached_policies = []
        self.tags = {tag["Key"]: tag["Value"] for tag in kwargs.get("Tags", [])}

    def describe(self):
        return {
            "Id": self.id,
            "Arn": self.arn,
            "Name": self.name,
            "PolicyTypes": self.policy_types,
        }

    def add_policy_type(self, policy_type):
        if policy_type not in self.SUPPORTED_POLICY_TYPES:
            raise InvalidInputException("You specified an invalid value.")

        if any(type["Type"] == policy_type for type in self.policy_types):
            raise PolicyTypeAlreadyEnabledException

        self.policy_types.append({"Type": policy_type, "Status": "ENABLED"})

    def remove_policy_type(self, policy_type):
        if not FakePolicy.supported_policy_type(policy_type):
            raise InvalidInputException("You specified an invalid value.")

        if all(type["Type"] != policy_type for type in self.policy_types):
            raise PolicyTypeNotEnabledException

        self.policy_types.remove({"Type": policy_type, "Status": "ENABLED"})


class FakePolicy(BaseModel):
    SUPPORTED_POLICY_TYPES = [
        "AISERVICES_OPT_OUT_POLICY",
        "BACKUP_POLICY",
        "SERVICE_CONTROL_POLICY",
        "TAG_POLICY",
    ]

    def __init__(self, organization, **kwargs):
        self.content = kwargs.get("Content")
        self.description = kwargs.get("Description")
        self.name = kwargs.get("Name")
        self.type = kwargs.get("Type")
        self.id = utils.make_random_policy_id()
        self.aws_managed = False
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.attachments = []

        if not FakePolicy.supported_policy_type(self.type):
            raise InvalidInputException("You specified an invalid value.")
        elif self.type == "AISERVICES_OPT_OUT_POLICY":
            self._arn_format = utils.AI_POLICY_ARN_FORMAT
        elif self.type == "SERVICE_CONTROL_POLICY":
            self._arn_format = utils.SCP_ARN_FORMAT
        else:
            raise NotImplementedError(
                "The {0} policy type has not been implemented".format(self.type)
            )

    @property
    def arn(self):
        return self._arn_format.format(
            self.master_account_id, self.organization_id, self.id
        )

    def describe(self):
        return {
            "Policy": {
                "PolicySummary": {
                    "Id": self.id,
                    "Arn": self.arn,
                    "Name": self.name,
                    "Description": self.description,
                    "Type": self.type,
                    "AwsManaged": self.aws_managed,
                },
                "Content": self.content,
            }
        }

    @staticmethod
    def supported_policy_type(policy_type):
        return policy_type in FakePolicy.SUPPORTED_POLICY_TYPES


class FakeServiceAccess(BaseModel):
    # List of trusted services, which support trusted access with Organizations
    # https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrated-services-list.html
    TRUSTED_SERVICES = [
        "aws-artifact-account-sync.amazonaws.com",
        "backup.amazonaws.com",
        "member.org.stacksets.cloudformation.amazonaws.com",
        "cloudtrail.amazonaws.com",
        "compute-optimizer.amazonaws.com",
        "config.amazonaws.com",
        "config-multiaccountsetup.amazonaws.com",
        "controltower.amazonaws.com",
        "ds.amazonaws.com",
        "fms.amazonaws.com",
        "guardduty.amazonaws.com",
        "access-analyzer.amazonaws.com",
        "license-manager.amazonaws.com",
        "license-manager.member-account.amazonaws.com.",
        "macie.amazonaws.com",
        "ram.amazonaws.com",
        "servicecatalog.amazonaws.com",
        "servicequotas.amazonaws.com",
        "sso.amazonaws.com",
        "ssm.amazonaws.com",
        "tagpolicies.tag.amazonaws.com",
    ]

    def __init__(self, **kwargs):
        if not self.trusted_service(kwargs["ServicePrincipal"]):
            raise InvalidInputException(
                "You specified an unrecognized service principal."
            )

        self.service_principal = kwargs["ServicePrincipal"]
        self.date_enabled = datetime.datetime.utcnow()

    def describe(self):
        return {
            "ServicePrincipal": self.service_principal,
            "DateEnabled": unix_time(self.date_enabled),
        }

    @staticmethod
    def trusted_service(service_principal):
        return service_principal in FakeServiceAccess.TRUSTED_SERVICES


class FakeDelegatedAdministrator(BaseModel):
    # List of services, which support a different Account to ba a delegated administrator
    # https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrated-services-list.html
    SUPPORTED_SERVICES = [
        "config-multiaccountsetup.amazonaws.com",
        "guardduty.amazonaws.com",
        "access-analyzer.amazonaws.com",
        "macie.amazonaws.com",
        "servicecatalog.amazonaws.com",
        "ssm.amazonaws.com",
    ]

    def __init__(self, account):
        self.account = account
        self.enabled_date = datetime.datetime.utcnow()
        self.services = {}

    def add_service_principal(self, service_principal):
        if service_principal in self.services:
            raise AccountAlreadyRegisteredException

        if not self.supported_service(service_principal):
            raise InvalidInputException(
                "You specified an unrecognized service principal."
            )

        self.services[service_principal] = {
            "ServicePrincipal": service_principal,
            "DelegationEnabledDate": unix_time(datetime.datetime.utcnow()),
        }

    def remove_service_principal(self, service_principal):
        if service_principal not in self.services:
            raise InvalidInputException(
                "You specified an unrecognized service principal."
            )

        self.services.pop(service_principal)

    def describe(self):
        admin = self.account.describe()
        admin["DelegationEnabledDate"] = unix_time(self.enabled_date)

        return admin

    @staticmethod
    def supported_service(service_principal):
        return service_principal in FakeDelegatedAdministrator.SUPPORTED_SERVICES


class OrganizationsBackend(BaseBackend):
    def __init__(self):
        self._reset()

    def _reset(self):
        self.org = None
        self.accounts = []
        self.ou = []
        self.policies = []
        self.services = []
        self.admins = []

    def _get_root_by_id(self, root_id):
        root = next((ou for ou in self.ou if ou.id == root_id), None)
        if not root:
            raise RootNotFoundException

        return root

    def create_organization(self, **kwargs):
        self.org = FakeOrganization(kwargs["FeatureSet"])
        root_ou = FakeRoot(self.org)
        self.ou.append(root_ou)
        master_account = FakeAccount(
            self.org, AccountName="master", Email=self.org.master_account_email
        )
        master_account.id = self.org.master_account_id
        self.accounts.append(master_account)
        default_policy = FakePolicy(
            self.org,
            Name="FullAWSAccess",
            Description="Allows access to every operation",
            Type="SERVICE_CONTROL_POLICY",
            Content=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
                }
            ),
        )
        default_policy.id = utils.DEFAULT_POLICY_ID
        default_policy.aws_managed = True
        self.policies.append(default_policy)
        self.attach_policy(PolicyId=default_policy.id, TargetId=root_ou.id)
        self.attach_policy(PolicyId=default_policy.id, TargetId=master_account.id)
        return self.org.describe()

    def describe_organization(self):
        if not self.org:
            raise AWSOrganizationsNotInUseException
        return self.org.describe()

    def delete_organization(self, **kwargs):
        self._reset()
        return {}

    def list_roots(self):
        return dict(Roots=[ou.describe() for ou in self.ou if isinstance(ou, FakeRoot)])

    def create_organizational_unit(self, **kwargs):
        new_ou = FakeOrganizationalUnit(self.org, **kwargs)
        self.ou.append(new_ou)
        self.attach_policy(PolicyId=utils.DEFAULT_POLICY_ID, TargetId=new_ou.id)
        return new_ou.describe()

    def update_organizational_unit(self, **kwargs):
        for ou in self.ou:
            if ou.name == kwargs["Name"]:
                raise DuplicateOrganizationalUnitException
        ou = self.get_organizational_unit_by_id(kwargs["OrganizationalUnitId"])
        ou.name = kwargs["Name"]
        return ou.describe()

    def get_organizational_unit_by_id(self, ou_id):
        ou = next((ou for ou in self.ou if ou.id == ou_id), None)
        if ou is None:
            raise RESTError(
                "OrganizationalUnitNotFoundException",
                "You specified an organizational unit that doesn't exist.",
            )
        return ou

    def validate_parent_id(self, parent_id):
        try:
            self.get_organizational_unit_by_id(parent_id)
        except RESTError:
            raise RESTError(
                "ParentNotFoundException", "You specified parent that doesn't exist."
            )
        return parent_id

    def describe_organizational_unit(self, **kwargs):
        ou = self.get_organizational_unit_by_id(kwargs["OrganizationalUnitId"])
        return ou.describe()

    def list_organizational_units_for_parent(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs["ParentId"])
        return dict(
            OrganizationalUnits=[
                {"Id": ou.id, "Arn": ou.arn, "Name": ou.name}
                for ou in self.ou
                if ou.parent_id == parent_id
            ]
        )

    def create_account(self, **kwargs):
        new_account = FakeAccount(self.org, **kwargs)
        self.accounts.append(new_account)
        self.attach_policy(PolicyId=utils.DEFAULT_POLICY_ID, TargetId=new_account.id)
        return new_account.create_account_status

    def get_account_by_id(self, account_id):
        account = next(
            (account for account in self.accounts if account.id == account_id), None
        )
        if account is None:
            raise AccountNotFoundException
        return account

    def get_account_by_attr(self, attr, value):
        account = next(
            (
                account
                for account in self.accounts
                if hasattr(account, attr) and getattr(account, attr) == value
            ),
            None,
        )
        if account is None:
            raise AccountNotFoundException
        return account

    def describe_account(self, **kwargs):
        account = self.get_account_by_id(kwargs["AccountId"])
        return dict(Account=account.describe())

    def describe_create_account_status(self, **kwargs):
        account = self.get_account_by_attr(
            "create_account_status_id", kwargs["CreateAccountRequestId"]
        )
        return account.create_account_status

    def list_create_account_status(self, **kwargs):
        requested_states = kwargs.get("States")
        if not requested_states:
            requested_states = ["IN_PROGRESS", "SUCCEEDED", "FAILED"]
        accountStatuses = []
        for account in self.accounts:
            create_account_status = account.create_account_status["CreateAccountStatus"]
            if create_account_status["State"] in requested_states:
                accountStatuses.append(create_account_status)
        token = kwargs.get("NextToken")
        if token:
            start = int(token)
        else:
            start = 0
        max_results = int(kwargs.get("MaxResults", 123))
        accounts_resp = accountStatuses[start : start + max_results]
        next_token = None
        if max_results and len(accountStatuses) > (start + max_results):
            next_token = str(len(accounts_resp))
        return dict(CreateAccountStatuses=accounts_resp, NextToken=next_token)

    def list_accounts(self):
        return dict(Accounts=[account.describe() for account in self.accounts])

    def list_accounts_for_parent(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs["ParentId"])
        return dict(
            Accounts=[
                account.describe()
                for account in self.accounts
                if account.parent_id == parent_id
            ]
        )

    def move_account(self, **kwargs):
        new_parent_id = self.validate_parent_id(kwargs["DestinationParentId"])
        self.validate_parent_id(kwargs["SourceParentId"])
        account = self.get_account_by_id(kwargs["AccountId"])
        index = self.accounts.index(account)
        self.accounts[index].parent_id = new_parent_id

    def list_parents(self, **kwargs):
        if re.compile(r"[0-9]{12}").match(kwargs["ChildId"]):
            child_object = self.get_account_by_id(kwargs["ChildId"])
        else:
            child_object = self.get_organizational_unit_by_id(kwargs["ChildId"])
        return dict(
            Parents=[
                {"Id": ou.id, "Type": ou.type}
                for ou in self.ou
                if ou.id == child_object.parent_id
            ]
        )

    def list_children(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs["ParentId"])
        if kwargs["ChildType"] == "ACCOUNT":
            obj_list = self.accounts
        elif kwargs["ChildType"] == "ORGANIZATIONAL_UNIT":
            obj_list = self.ou
        else:
            raise InvalidInputException("You specified an invalid value.")
        return dict(
            Children=[
                {"Id": obj.id, "Type": kwargs["ChildType"]}
                for obj in obj_list
                if obj.parent_id == parent_id
            ]
        )

    def create_policy(self, **kwargs):
        new_policy = FakePolicy(self.org, **kwargs)
        for policy in self.policies:
            if kwargs["Name"] == policy.name:
                raise DuplicatePolicyException
        self.policies.append(new_policy)
        return new_policy.describe()

    def describe_policy(self, **kwargs):
        if re.compile(utils.POLICY_ID_REGEX).match(kwargs["PolicyId"]):
            policy = next(
                (p for p in self.policies if p.id == kwargs["PolicyId"]), None
            )
            if policy is None:
                raise RESTError(
                    "PolicyNotFoundException",
                    "You specified a policy that doesn't exist.",
                )
        else:
            raise InvalidInputException("You specified an invalid value.")
        return policy.describe()

    def get_policy_by_id(self, policy_id):
        policy = next(
            (policy for policy in self.policies if policy.id == policy_id), None
        )
        if policy is None:
            raise RESTError(
                "PolicyNotFoundException",
                "We can't find a policy with the PolicyId that you specified.",
            )
        return policy

    def update_policy(self, **kwargs):
        policy = self.get_policy_by_id(kwargs["PolicyId"])
        policy.name = kwargs.get("Name", policy.name)
        policy.description = kwargs.get("Description", policy.description)
        policy.content = kwargs.get("Content", policy.content)
        return policy.describe()

    def attach_policy(self, **kwargs):
        policy = self.get_policy_by_id(kwargs["PolicyId"])
        if re.compile(utils.ROOT_ID_REGEX).match(kwargs["TargetId"]) or re.compile(
            utils.OU_ID_REGEX
        ).match(kwargs["TargetId"]):
            ou = next((ou for ou in self.ou if ou.id == kwargs["TargetId"]), None)
            if ou is not None:
                if ou not in ou.attached_policies:
                    ou.attached_policies.append(policy)
                    policy.attachments.append(ou)
            else:
                raise RESTError(
                    "OrganizationalUnitNotFoundException",
                    "You specified an organizational unit that doesn't exist.",
                )
        elif re.compile(utils.ACCOUNT_ID_REGEX).match(kwargs["TargetId"]):
            account = next(
                (a for a in self.accounts if a.id == kwargs["TargetId"]), None
            )
            if account is not None:
                if account not in account.attached_policies:
                    account.attached_policies.append(policy)
                    policy.attachments.append(account)
            else:
                raise AccountNotFoundException
        else:
            raise InvalidInputException("You specified an invalid value.")

    def list_policies(self, **kwargs):
        return dict(
            Policies=[p.describe()["Policy"]["PolicySummary"] for p in self.policies]
        )

    def delete_policy(self, **kwargs):
        for idx, policy in enumerate(self.policies):
            if policy.id == kwargs["PolicyId"]:
                if self.list_targets_for_policy(PolicyId=policy.id)["Targets"]:
                    raise RESTError(
                        "PolicyInUseException",
                        "The policy is attached to one or more entities. You must detach it from all roots, OUs, and accounts before performing this operation.",
                    )
                del self.policies[idx]
                return
        raise RESTError(
            "PolicyNotFoundException",
            "We can't find a policy with the PolicyId that you specified.",
        )

    def list_policies_for_target(self, **kwargs):
        filter = kwargs["Filter"]

        if re.match(utils.ROOT_ID_REGEX, kwargs["TargetId"]):
            obj = next((ou for ou in self.ou if ou.id == kwargs["TargetId"]), None)
            if obj is None:
                raise TargetNotFoundException
        elif re.compile(utils.OU_ID_REGEX).match(kwargs["TargetId"]):
            obj = next((ou for ou in self.ou if ou.id == kwargs["TargetId"]), None)
            if obj is None:
                raise RESTError(
                    "OrganizationalUnitNotFoundException",
                    "You specified an organizational unit that doesn't exist.",
                )
        elif re.compile(utils.ACCOUNT_ID_REGEX).match(kwargs["TargetId"]):
            obj = next((a for a in self.accounts if a.id == kwargs["TargetId"]), None)
            if obj is None:
                raise AccountNotFoundException
        else:
            raise InvalidInputException("You specified an invalid value.")

        if not FakePolicy.supported_policy_type(filter):
            raise InvalidInputException("You specified an invalid value.")

        if filter not in ["AISERVICES_OPT_OUT_POLICY", "SERVICE_CONTROL_POLICY"]:
            raise NotImplementedError(
                "The {0} policy type has not been implemented".format(filter)
            )

        return dict(
            Policies=[
                p.describe()["Policy"]["PolicySummary"]
                for p in obj.attached_policies
                if p.type == filter
            ]
        )

    def _get_resource_for_tagging(self, resource_id):
        if utils.fullmatch(
            re.compile(utils.OU_ID_REGEX), resource_id
        ) or utils.fullmatch(utils.ROOT_ID_REGEX, resource_id):
            resource = next((a for a in self.ou if a.id == resource_id), None)
        elif utils.fullmatch(re.compile(utils.ACCOUNT_ID_REGEX), resource_id):
            resource = next((a for a in self.accounts if a.id == resource_id), None)
        elif utils.fullmatch(re.compile(utils.POLICY_ID_REGEX), resource_id):
            resource = next((a for a in self.policies if a.id == resource_id), None)
        else:
            raise InvalidInputException(
                "You provided a value that does not match the required pattern."
            )

        if resource is None:
            raise TargetNotFoundException

        return resource

    def list_targets_for_policy(self, **kwargs):
        if re.compile(utils.POLICY_ID_REGEX).match(kwargs["PolicyId"]):
            policy = next(
                (p for p in self.policies if p.id == kwargs["PolicyId"]), None
            )
            if policy is None:
                raise RESTError(
                    "PolicyNotFoundException",
                    "You specified a policy that doesn't exist.",
                )
        else:
            raise InvalidInputException("You specified an invalid value.")
        objects = [
            {"TargetId": obj.id, "Arn": obj.arn, "Name": obj.name, "Type": obj.type}
            for obj in policy.attachments
        ]
        return dict(Targets=objects)

    def tag_resource(self, **kwargs):
        resource = self._get_resource_for_tagging(kwargs["ResourceId"])
        new_tags = {tag["Key"]: tag["Value"] for tag in kwargs["Tags"]}
        resource.tags.update(new_tags)

    def list_tags_for_resource(self, **kwargs):
        resource = self._get_resource_for_tagging(kwargs["ResourceId"])
        tags = [{"Key": key, "Value": value} for key, value in resource.tags.items()]
        return dict(Tags=tags)

    def untag_resource(self, **kwargs):
        resource = self._get_resource_for_tagging(kwargs["ResourceId"])
        for key in kwargs["TagKeys"]:
            resource.tags.pop(key, None)

    def enable_aws_service_access(self, **kwargs):
        service = FakeServiceAccess(**kwargs)

        # enabling an existing service results in no changes
        if any(
            service["ServicePrincipal"] == kwargs["ServicePrincipal"]
            for service in self.services
        ):
            return

        self.services.append(service.describe())

    def list_aws_service_access_for_organization(self):
        return dict(EnabledServicePrincipals=self.services)

    def disable_aws_service_access(self, **kwargs):
        if not FakeServiceAccess.trusted_service(kwargs["ServicePrincipal"]):
            raise InvalidInputException(
                "You specified an unrecognized service principal."
            )

        service_principal = next(
            (
                service
                for service in self.services
                if service["ServicePrincipal"] == kwargs["ServicePrincipal"]
            ),
            None,
        )

        if service_principal:
            self.services.remove(service_principal)

    def register_delegated_administrator(self, **kwargs):
        account_id = kwargs["AccountId"]

        if account_id == ACCOUNT_ID:
            raise ConstraintViolationException(
                "You cannot register master account/yourself as delegated administrator for your organization."
            )

        account = self.get_account_by_id(account_id)

        admin = next(
            (admin for admin in self.admins if admin.account.id == account_id), None
        )
        if admin is None:
            admin = FakeDelegatedAdministrator(account)
            self.admins.append(admin)

        admin.add_service_principal(kwargs["ServicePrincipal"])

    def list_delegated_administrators(self, **kwargs):
        admins = self.admins
        service = kwargs.get("ServicePrincipal")

        if service:
            if not FakeDelegatedAdministrator.supported_service(service):
                raise InvalidInputException(
                    "You specified an unrecognized service principal."
                )

            admins = [admin for admin in admins if service in admin.services]

        delegated_admins = [admin.describe() for admin in admins]

        return dict(DelegatedAdministrators=delegated_admins)

    def list_delegated_services_for_account(self, **kwargs):
        admin = next(
            (admin for admin in self.admins if admin.account.id == kwargs["AccountId"]),
            None,
        )
        if admin is None:
            account = next(
                (
                    account
                    for account in self.accounts
                    if account.id == kwargs["AccountId"]
                ),
                None,
            )
            if account:
                raise AccountNotRegisteredException

            raise AWSOrganizationsNotInUseException

        services = [service for service in admin.services.values()]

        return dict(DelegatedServices=services)

    def deregister_delegated_administrator(self, **kwargs):
        account_id = kwargs["AccountId"]
        service = kwargs["ServicePrincipal"]

        if account_id == ACCOUNT_ID:
            raise ConstraintViolationException(
                "You cannot register master account/yourself as delegated administrator for your organization."
            )

        admin = next(
            (admin for admin in self.admins if admin.account.id == account_id), None,
        )
        if admin is None:
            account = next(
                (
                    account
                    for account in self.accounts
                    if account.id == kwargs["AccountId"]
                ),
                None,
            )
            if account:
                raise AccountNotRegisteredException

            raise AccountNotFoundException

        admin.remove_service_principal(service)

        # remove account, when no services attached
        if not admin.services:
            self.admins.remove(admin)

    def enable_policy_type(self, **kwargs):
        root = self._get_root_by_id(kwargs["RootId"])

        root.add_policy_type(kwargs["PolicyType"])

        return dict(Root=root.describe())

    def disable_policy_type(self, **kwargs):
        root = self._get_root_by_id(kwargs["RootId"])

        root.remove_policy_type(kwargs["PolicyType"])

        return dict(Root=root.describe())

    def detach_policy(self, **kwargs):
        policy = self.get_policy_by_id(kwargs["PolicyId"])
        root_id_regex = utils.ROOT_ID_REGEX
        ou_id_regex = utils.OU_ID_REGEX
        account_id_regex = utils.ACCOUNT_ID_REGEX
        target_id = kwargs["TargetId"]

        if re.match(root_id_regex, target_id) or re.match(ou_id_regex, target_id):
            ou = next((ou for ou in self.ou if ou.id == target_id), None)
            if ou is not None:
                if ou in ou.attached_policies:
                    ou.attached_policies.remove(policy)
                    policy.attachments.remove(ou)
            else:
                raise RESTError(
                    "OrganizationalUnitNotFoundException",
                    "You specified an organizational unit that doesn't exist.",
                )
        elif re.match(account_id_regex, target_id):
            account = next(
                (account for account in self.accounts if account.id == target_id), None,
            )
            if account is not None:
                if account in account.attached_policies:
                    account.attached_policies.remove(policy)
                    policy.attachments.remove(account)
            else:
                raise AccountNotFoundException
        else:
            raise InvalidInputException("You specified an invalid value.")


organizations_backend = OrganizationsBackend()
