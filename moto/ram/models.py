import re
import string
from datetime import datetime
import random
from uuid import uuid4

from moto.core import BaseBackend, BaseModel, ACCOUNT_ID
from moto.core.utils import unix_time, BackendDict
from moto.organizations import organizations_backends
from moto.ram.exceptions import (
    MalformedArnException,
    InvalidParameterException,
    UnknownResourceException,
    OperationNotPermittedException,
)


def random_resource_id(size):
    return "".join(random.choice(string.digits + "abcdef") for _ in range(size))


class ResourceShare(BaseModel):
    # List of shareable resources can be found here
    # https://docs.aws.amazon.com/ram/latest/userguide/shareable.html
    SHAREABLE_RESOURCES = [
        "cluster",  # Amazon Aurora cluster
        "component",  # Amazon EC2 Image Builder component
        "group",  # AWS Resource Groups
        "image",  # Amazon EC2 Image Builder image
        "image-recipe",  # Amazon EC2 Image Builder image recipe
        "license-configuration",  # AWS License Manager configuration
        "mesh",  # AWS App Mesh
        "prefix-list",  # Amazon EC2 prefix list
        "project",  # AWS CodeBuild project
        "report-group",  # AWS CodeBuild report group
        "resolver-rule",  # Amazon Route 53 forwarding rule
        "subnet",  # Amazon EC2 subnet
        "transit-gateway",  # Amazon EC2 transit gateway
    ]

    def __init__(self, region, **kwargs):
        self.region = region

        self.allow_external_principals = kwargs.get("allowExternalPrincipals", True)
        self.arn = "arn:aws:ram:{0}:{1}:resource-share/{2}".format(
            self.region, ACCOUNT_ID, uuid4()
        )
        self.creation_time = datetime.utcnow()
        self.feature_set = "STANDARD"
        self.last_updated_time = datetime.utcnow()
        self.name = kwargs["name"]
        self.owning_account_id = ACCOUNT_ID
        self.principals = []
        self.resource_arns = []
        self.status = "ACTIVE"

    @property
    def organizations_backend(self):
        return organizations_backends["global"]

    def add_principals(self, principals):
        for principal in principals:
            match = re.search(
                r"^arn:aws:organizations::\d{12}:organization/(o-\w+)$", principal
            )
            if match:
                organization = self.organizations_backend.describe_organization()
                if principal == organization["Organization"]["Arn"]:
                    continue
                else:
                    raise UnknownResourceException(
                        "Organization {} could not be found.".format(match.group(1))
                    )

            match = re.search(
                r"^arn:aws:organizations::\d{12}:ou/(o-\w+)/(ou-[\w-]+)$", principal
            )
            if match:
                roots = self.organizations_backend.list_roots()
                root_id = next(
                    (
                        root["Id"]
                        for root in roots["Roots"]
                        if root["Name"] == "Root" and match.group(1) in root["Arn"]
                    ),
                    None,
                )

                if root_id:
                    ous = (
                        self.organizations_backend.list_organizational_units_for_parent(
                            ParentId=root_id
                        )
                    )
                    if any(principal == ou["Arn"] for ou in ous["OrganizationalUnits"]):
                        continue

                raise UnknownResourceException(
                    "OrganizationalUnit {} in unknown organization could not be found.".format(
                        match.group(2)
                    )
                )

            if not re.match(r"^\d{12}$", principal):
                raise InvalidParameterException(
                    "Principal ID {} is malformed. "
                    "Verify the ID and try again.".format(principal)
                )

        for principal in principals:
            self.principals.append(principal)

    def add_resources(self, resource_arns):
        for resource in resource_arns:
            match = re.search(
                r"^arn:aws:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:([a-z-]+)[/:].*$", resource
            )
            if not match:
                raise MalformedArnException(
                    "The specified resource ARN {} is not valid. "
                    "Verify the ARN and try again.".format(resource)
                )

            if match.group(1) not in self.SHAREABLE_RESOURCES:
                raise MalformedArnException(
                    "You cannot share the selected resource type."
                )

        for resource in resource_arns:
            self.resource_arns.append(resource)

    def delete(self):
        self.last_updated_time = datetime.utcnow()
        self.status = "DELETED"

    def describe(self):
        return {
            "allowExternalPrincipals": self.allow_external_principals,
            "creationTime": unix_time(self.creation_time),
            "featureSet": self.feature_set,
            "lastUpdatedTime": unix_time(self.last_updated_time),
            "name": self.name,
            "owningAccountId": self.owning_account_id,
            "resourceShareArn": self.arn,
            "status": self.status,
        }

    def update(self, **kwargs):
        self.allow_external_principals = kwargs.get(
            "allowExternalPrincipals", self.allow_external_principals
        )
        self.last_updated_time = datetime.utcnow()
        self.name = kwargs.get("name", self.name)


class ResourceAccessManagerBackend(BaseBackend):
    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name
        self.resource_shares = []

    @property
    def organizations_backend(self):
        return organizations_backends["global"]

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_resource_share(self, **kwargs):
        resource = ResourceShare(self.region_name, **kwargs)
        resource.add_principals(kwargs.get("principals", []))
        resource.add_resources(kwargs.get("resourceArns", []))

        self.resource_shares.append(resource)

        response = resource.describe()
        response.pop("featureSet")

        return dict(resourceShare=response)

    def get_resource_shares(self, **kwargs):
        owner = kwargs["resourceOwner"]

        if owner not in ["SELF", "OTHER-ACCOUNTS"]:
            raise InvalidParameterException(
                "{} is not a valid resource owner. "
                "Specify either SELF or OTHER-ACCOUNTS and try again.".format(owner)
            )

        if owner == "OTHER-ACCOUNTS":
            raise NotImplementedError(
                "Value 'OTHER-ACCOUNTS' for parameter 'resourceOwner' not implemented."
            )

        resouces = [resource.describe() for resource in self.resource_shares]

        return dict(resourceShares=resouces)

    def update_resource_share(self, **kwargs):
        arn = kwargs["resourceShareArn"]

        resource = next(
            (resource for resource in self.resource_shares if arn == resource.arn), None
        )

        if not resource:
            raise UnknownResourceException(
                "ResourceShare {} could not be found.".format(arn)
            )

        resource.update(**kwargs)
        response = resource.describe()
        response.pop("featureSet")

        return dict(resourceShare=response)

    def delete_resource_share(self, arn):
        resource = next(
            (resource for resource in self.resource_shares if arn == resource.arn), None
        )

        if not resource:
            raise UnknownResourceException(
                "ResourceShare {} could not be found.".format(arn)
            )

        resource.delete()

        return dict(returnValue=True)

    def enable_sharing_with_aws_organization(self):
        if not self.organizations_backend.org:
            raise OperationNotPermittedException

        return dict(returnValue=True)


ram_backends = BackendDict(ResourceAccessManagerBackend, "ram")
