import re
import string
from typing import Any, Dict, List

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import unix_time, utcnow
from moto.moto_api._internal import mock_random as random
from moto.organizations.models import OrganizationsBackend, organizations_backends
from moto.ram.exceptions import (
    InvalidParameterException,
    MalformedArnException,
    OperationNotPermittedException,
    UnknownResourceException,
)
from moto.utilities.utils import get_partition


def random_resource_id(size: int) -> str:
    return "".join(random.choice(string.digits + "abcdef") for _ in range(size))


class ResourceShare(BaseModel):
    # List of shareable resources can be found here
    # https://docs.aws.amazon.com/ram/latest/userguide/shareable.html
    SHAREABLE_RESOURCES = [
        "cluster",  # Amazon Aurora cluster
        "component",  # Amazon EC2 Image Builder component
        "core-network",  # Amazon Network Manager core network
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
        "transit-gateway",  # Amazon EC2 transit gateway,
        "database",  # Amazon Glue database
        "table",  # Amazon Glue table
        "catalog",  # Amazon Glue catalog
    ]

    def __init__(self, account_id: str, region: str, **kwargs: Any):
        self.account_id = account_id
        self.region = region
        self.partition = get_partition(region)

        self.allow_external_principals = kwargs.get("allowExternalPrincipals", True)
        self.arn = f"arn:{get_partition(self.region)}:ram:{self.region}:{account_id}:resource-share/{random.uuid4()}"
        self.creation_time = utcnow()
        self.feature_set = "STANDARD"
        self.last_updated_time = utcnow()
        self.name = kwargs["name"]
        self.owning_account_id = account_id
        self.principals: List[str] = []
        self.resource_arns: List[str] = []
        self.status = "ACTIVE"

    @property
    def organizations_backend(self) -> OrganizationsBackend:
        return organizations_backends[self.account_id][self.partition]

    def add_principals(self, principals: List[str]) -> None:
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
                        f"Organization {match.group(1)} could not be found."
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
                    (
                        ous,
                        _,
                    ) = self.organizations_backend.list_organizational_units_for_parent(
                        parent_id=root_id
                    )
                    if any(principal == ou.arn for ou in ous):
                        continue

                raise UnknownResourceException(
                    f"OrganizationalUnit {match.group(2)} in unknown organization could not be found."
                )

            if not re.match(r"^\d{12}$", principal):
                raise InvalidParameterException(
                    f"Principal ID {principal} is malformed. Verify the ID and try again."
                )

        for principal in principals:
            self.principals.append(principal)

    def add_resources(self, resource_arns: List[str]) -> None:
        for resource in resource_arns:
            match = re.search(
                r"^arn:aws:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:([a-z-]+)[/:].*$", resource
            )
            if not match:
                raise MalformedArnException(
                    f"The specified resource ARN {resource} is not valid. Verify the ARN and try again."
                )

            if match.group(1) not in self.SHAREABLE_RESOURCES:
                raise MalformedArnException(
                    "You cannot share the selected resource type."
                )

        for resource in resource_arns:
            self.resource_arns.append(resource)

    def delete(self) -> None:
        self.last_updated_time = utcnow()
        self.status = "DELETED"

    def describe(self) -> Dict[str, Any]:
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

    def update(self, **kwargs: Any) -> None:
        self.allow_external_principals = kwargs.get(
            "allowExternalPrincipals", self.allow_external_principals
        )
        self.last_updated_time = utcnow()
        self.name = kwargs.get("name", self.name)


class ResourceAccessManagerBackend(BaseBackend):
    RESOURCE_TYPES = [  # List of resource types based on SHAREABLE_RESOURCES
        {
            "resourceType": "rds:Cluster",
            "serviceName": "rds",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "imagebuilder:Component",
            "serviceName": "imagebuilder",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "networkmanager:CoreNetwork",
            "serviceName": "networkmanager",
            "resourceRegionScope": "GLOBAL",
        },
        {
            "resourceType": "resource-groups:Group",
            "serviceName": "resource-groups",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "imagebuilder:Image",
            "serviceName": "imagebuilder",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "imagebuilder:ImageRecipe",
            "serviceName": "imagebuilder",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "license-manager:LicenseConfiguration",
            "serviceName": "license-manager",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "appmesh:Mesh",
            "serviceName": "appmesh",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "ec2:PrefixList",
            "serviceName": "ec2",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "codebuild:Project",
            "serviceName": "codebuild",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "codebuild:ReportGroup",
            "serviceName": "codebuild",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "route53resolver:ResolverRule",
            "serviceName": "route53resolver",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "ec2:Subnet",
            "serviceName": "ec2",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "ec2:TransitGatewayMulticastDomain",
            "serviceName": "ec2",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "glue:Database",
            "serviceName": "glue",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "glue:Table",
            "serviceName": "glue",
            "resourceRegionScope": "REGIONAL",
        },
        {
            "resourceType": "glue:Catalog",
            "serviceName": "glue",
            "resourceRegionScope": "REGIONAL",
        },
    ]

    PERMISSION_TYPES = ["ALL", "AWS", "LOCAL"]

    MANAGED_PERMISSIONS = [
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionRDSCluster",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionRDSCluster",
            "resourceType": "rds:Cluster",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:16.671000",
            "lastUpdatedTime": "2022-06-30 17:04:16.671000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionImageBuilderComponent",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionImageBuilderComponent",
            "resourceType": "imagebuilder:Component",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:21.977000",
            "lastUpdatedTime": "2022-06-30 17:04:21.977000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionsNetworkManagerCoreNetwork",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionsNetworkManagerCoreNetwork",
            "resourceType": "networkmanager:CoreNetwork",
            "status": "ATTACHABLE",
            "creationTime": "2024-10-23 16:34:51.604000",
            "lastUpdatedTime": "2024-10-23 16:34:51.604000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMTransitGatewayPermissionsNetworkManagerCoreNetwork",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMTransitGatewayPermissionsNetworkManagerCoreNetwork",
            "resourceType": "networkmanager:CoreNetwork",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:03:48.071000",
            "lastUpdatedTime": "2022-06-30 17:03:48.071000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMVPCPermissionsNetworkManagerCoreNetwork",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMVPCPermissionsNetworkManagerCoreNetwork",
            "resourceType": "networkmanager:CoreNetwork",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:03:46.477000",
            "lastUpdatedTime": "2022-06-30 17:03:46.477000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionResourceGroup",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionResourceGroup",
            "resourceType": "resource-groups:Group",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:10.914000",
            "lastUpdatedTime": "2022-06-30 17:04:10.914000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionImageBuilderImage",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionImageBuilderImage",
            "resourceType": "imagebuilder:Image",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:21.201000",
            "lastUpdatedTime": "2022-06-30 17:04:21.201000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionImageBuilderImageRecipe",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionImageBuilderImageRecipe",
            "resourceType": "imagebuilder:ImageRecipe",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:22.832000",
            "lastUpdatedTime": "2022-06-30 17:04:22.832000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionLicenseConfiguration",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionLicenseConfiguration",
            "resourceType": "license-manager:LicenseConfiguration",
            "status": "ATTACHABLE",
            "creationTime": "2024-01-31 16:36:13.664000",
            "lastUpdatedTime": "2024-01-31 16:36:13.664000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionAppMesh",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionAppMesh",
            "resourceType": "appmesh:Mesh",
            "status": "ATTACHABLE",
            "creationTime": "2023-03-28 12:27:55.910000",
            "lastUpdatedTime": "2023-03-28 12:27:55.910000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionPrefixList",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionPrefixList",
            "resourceType": "ec2:PrefixList",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:20.594000",
            "lastUpdatedTime": "2022-06-30 17:04:20.594000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionCodeBuildProject",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionCodeBuildProject",
            "resourceType": "codebuild:Project",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:17.595000",
            "lastUpdatedTime": "2022-06-30 17:04:17.595000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionCodeBuildReportGroup",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionCodeBuildReportGroup",
            "resourceType": "codebuild:ReportGroup",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:17.761000",
            "lastUpdatedTime": "2022-06-30 17:04:17.761000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionResolverRule",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionResolverRule",
            "resourceType": "route53resolver:ResolverRule",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:14.752000",
            "lastUpdatedTime": "2022-06-30 17:04:14.752000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionSubnet",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionSubnet",
            "resourceType": "ec2:Subnet",
            "status": "ATTACHABLE",
            "creationTime": "2024-10-30 15:11:41.358000",
            "lastUpdatedTime": "2024-10-30 15:11:41.358000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionTransitGatewayMulticastDomain",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionTransitGatewayMulticastDomain",
            "resourceType": "ec2:TransitGatewayMulticastDomain",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:13.461000",
            "lastUpdatedTime": "2022-06-30 17:04:13.461000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionGlueDatabase",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionGlueDatabase",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:25.912000",
            "lastUpdatedTime": "2022-06-30 17:04:25.912000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMLFEnabledGlueAllTablesReadWriteForDatabase",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMLFEnabledGlueAllTablesReadWriteForDatabase",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2023-06-27 17:05:24.471000",
            "lastUpdatedTime": "2023-06-27 17:05:24.471000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMLFEnabledGlueDatabaseReadWrite",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMLFEnabledGlueDatabaseReadWrite",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2023-06-27 17:05:27.153000",
            "lastUpdatedTime": "2023-06-27 17:05:27.153000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueAllTablesReadWriteForDatabase",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueAllTablesReadWriteForDatabase",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:19:43.345000",
            "lastUpdatedTime": "2022-10-27 14:19:43.345000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueDatabaseReadWrite",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueDatabaseReadWrite",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:20:08.415000",
            "lastUpdatedTime": "2022-10-27 14:20:08.415000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueTableReadWriteForDatabase",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueTableReadWriteForDatabase",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:19:17.062000",
            "lastUpdatedTime": "2022-10-27 14:19:17.062000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionLFTagGlueDatabaseReadWrite",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMPermissionLFTagGlueDatabaseReadWrite",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:22:14.138000",
            "lastUpdatedTime": "2022-10-27 14:22:14.138000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionLFTagGlueTableReadWriteForDatabase",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMPermissionLFTagGlueTableReadWriteForDatabase",
            "resourceType": "glue:Database",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:21:49.920000",
            "lastUpdatedTime": "2022-10-27 14:21:49.920000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionGlueTable",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionGlueTable",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:24.372000",
            "lastUpdatedTime": "2022-06-30 17:04:24.372000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMLFEnabledGlueDatabaseReadWriteForTable",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMLFEnabledGlueDatabaseReadWriteForTable",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2023-06-27 17:05:33.534000",
            "lastUpdatedTime": "2023-06-27 17:05:33.534000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMLFEnabledGlueTableReadWrite",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMLFEnabledGlueTableReadWrite",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2023-06-27 17:05:21.095000",
            "lastUpdatedTime": "2023-06-27 17:05:21.095000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueDatabaseReadWriteForTable",
            "version": "2",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueDatabaseReadWriteForTable",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:09.034000",
            "lastUpdatedTime": "2022-06-30 17:04:09.034000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueTableReadWrite",
            "version": "2",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueTableReadWrite",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:03.947000",
            "lastUpdatedTime": "2022-06-30 17:04:03.947000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionLFTagGlueDatabaseReadWriteForTable",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMPermissionLFTagGlueDatabaseReadWriteForTable",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:22:26.191000",
            "lastUpdatedTime": "2022-10-27 14:22:26.191000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionLFTagGlueTableReadWrite",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMPermissionLFTagGlueTableReadWrite",
            "resourceType": "glue:Table",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:22:01.908000",
            "lastUpdatedTime": "2022-10-27 14:22:01.908000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionGlueCatalog",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMDefaultPermissionGlueCatalog",
            "resourceType": "glue:Catalog",
            "status": "ATTACHABLE",
            "creationTime": "2022-06-30 17:04:26.612000",
            "lastUpdatedTime": "2022-06-30 17:04:26.612000",
            "isResourceTypeDefault": True,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueAllTablesReadWriteForCatalog",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueAllTablesReadWriteForCatalog",
            "resourceType": "glue:Catalog",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:19:56.250000",
            "lastUpdatedTime": "2022-10-27 14:19:56.250000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueDatabaseReadWriteForCatalog",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueDatabaseReadWriteForCatalog",
            "resourceType": "glue:Catalog",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:20:20.322000",
            "lastUpdatedTime": "2022-10-27 14:20:20.322000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionGlueTableReadWriteForCatalog",
            "version": "3",
            "defaultVersion": True,
            "name": "AWSRAMPermissionGlueTableReadWriteForCatalog",
            "resourceType": "glue:Catalog",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:19:30.644000",
            "lastUpdatedTime": "2022-10-27 14:19:30.644000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionLFTagGlueDatabaseReadWriteForCatalog",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMPermissionLFTagGlueDatabaseReadWriteForCatalog",
            "resourceType": "glue:Catalog",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:22:37.435000",
            "lastUpdatedTime": "2022-10-27 14:22:37.435000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
        {
            "arn": "arn:aws:ram::aws:permission/AWSRAMPermissionLFTagGlueTableReadWriteForCatalog",
            "version": "1",
            "defaultVersion": True,
            "name": "AWSRAMPermissionLFTagGlueTableReadWriteForCatalog",
            "resourceType": "glue:Catalog",
            "status": "ATTACHABLE",
            "creationTime": "2022-10-27 14:21:37.593000",
            "lastUpdatedTime": "2022-10-27 14:21:37.593000",
            "isResourceTypeDefault": False,
            "permissionType": "AWS_MANAGED",
        },
    ]

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.resource_shares: List[ResourceShare] = []

    @property
    def organizations_backend(self) -> OrganizationsBackend:
        return organizations_backends[self.account_id][self.partition]

    def create_resource_share(self, **kwargs: Any) -> Dict[str, Any]:
        resource = ResourceShare(self.account_id, self.region_name, **kwargs)
        resource.add_principals(kwargs.get("principals", []))
        resource.add_resources(kwargs.get("resourceArns", []))

        self.resource_shares.append(resource)

        response = resource.describe()
        response.pop("featureSet")

        return dict(resourceShare=response)

    def get_resource_shares(self, **kwargs: Any) -> Dict[str, Any]:
        owner = kwargs["resourceOwner"]

        if owner not in ["SELF", "OTHER-ACCOUNTS"]:
            raise InvalidParameterException(
                f"{owner} is not a valid resource owner. "
                "Specify either SELF or OTHER-ACCOUNTS and try again."
            )

        if owner == "OTHER-ACCOUNTS":
            raise NotImplementedError(
                "Value 'OTHER-ACCOUNTS' for parameter 'resourceOwner' not implemented."
            )

        resouces = [resource.describe() for resource in self.resource_shares]

        return dict(resourceShares=resouces)

    def update_resource_share(self, **kwargs: Any) -> Dict[str, Any]:
        arn = kwargs["resourceShareArn"]

        resource = next(
            (resource for resource in self.resource_shares if arn == resource.arn), None
        )

        if not resource:
            raise UnknownResourceException(f"ResourceShare {arn} could not be found.")

        resource.update(**kwargs)
        response = resource.describe()
        response.pop("featureSet")

        return dict(resourceShare=response)

    def delete_resource_share(self, arn: str) -> Dict[str, Any]:
        resource = next(
            (resource for resource in self.resource_shares if arn == resource.arn), None
        )

        if not resource:
            raise UnknownResourceException(f"ResourceShare {arn} could not be found.")

        resource.delete()

        return dict(returnValue=True)

    def enable_sharing_with_aws_organization(self) -> Dict[str, Any]:
        if not self.organizations_backend.org:
            raise OperationNotPermittedException

        return dict(returnValue=True)

    def get_resource_share_associations(self, **kwargs: Any) -> Dict[str, Any]:
        association_type = kwargs["associationType"]
        if association_type not in ["PRINCIPAL", "RESOURCE"]:
            raise InvalidParameterException(
                f"{association_type} is not a valid association type. "
                "Specify either PRINCIPAL or RESOURCE and try again."
            )

        association_status = kwargs.get("associationStatus")
        if association_status and association_status not in [
            "ASSOCIATING",
            "ASSOCIATED",
            "FAILED",
            "DISASSOCIATING",
            "DISASSOCIATED",
        ]:
            raise InvalidParameterException(
                f"{association_status} is not a valid association status."
            )

        resource_share_arns = kwargs.get("resourceShareArns", [])
        resource_arn = kwargs.get("resourceArn")
        principal = kwargs.get("principal")

        if association_type == "PRINCIPAL" and resource_arn:
            raise InvalidParameterException(
                "You cannot specify a resource ARN when the association type is PRINCIPAL."
            )
        if association_type == "RESOURCE" and principal:
            raise InvalidParameterException(
                "You cannot specify a principal when the association type is RESOURCE."
            )

        associations = []
        for resource_share in self.resource_shares:
            if resource_share_arns and resource_share.arn not in resource_share_arns:
                continue

            if association_type == "PRINCIPAL":
                for principal_id in resource_share.principals:
                    if principal and principal != principal_id:
                        continue
                    associations.append(
                        {
                            "resourceShareArn": resource_share.arn,
                            "resourceShareName": resource_share.name,
                            "associatedEntity": principal_id,
                            "associationType": "PRINCIPAL",
                            "status": association_status or "ASSOCIATED",
                            "creationTime": unix_time(resource_share.creation_time),
                            "lastUpdatedTime": unix_time(
                                resource_share.last_updated_time
                            ),
                            "external": False,
                        }
                    )
            else:  # RESOURCE
                for resource_id in resource_share.resource_arns:
                    if resource_arn and resource_arn != resource_id:
                        continue
                    associations.append(
                        {
                            "resourceShareArn": resource_share.arn,
                            "resourceShareName": resource_share.name,
                            "associatedEntity": resource_id,
                            "associationType": "RESOURCE",
                            "status": association_status or "ASSOCIATED",
                            "creationTime": unix_time(resource_share.creation_time),
                            "lastUpdatedTime": unix_time(
                                resource_share.last_updated_time
                            ),
                            "external": False,
                        }
                    )

        return dict(resourceShareAssociations=associations)

    def list_resource_types(self, **kwargs: Any) -> Dict[str, Any]:
        resource_region_scope = kwargs.get("resourceRegionScope", "ALL")

        if resource_region_scope not in ["ALL", "REGIONAL", "GLOBAL"]:
            raise InvalidParameterException(
                f"{resource_region_scope} is not a valid resource region "
                "scope value. Specify a valid value and try again."
            )

        if resource_region_scope == "ALL":
            resource_types = self.RESOURCE_TYPES
        else:
            resource_types = [
                resource_type
                for resource_type in self.RESOURCE_TYPES
                if resource_type["resourceRegionScope"] == resource_region_scope
            ]

        return dict(resourceTypes=resource_types)

    def list_permissions(self, **kwargs: Any) -> Dict[str, Any]:
        resource_type = kwargs.get("resourceType")
        permission_type = kwargs.get("permissionType", "ALL")
        permission_types_relation = {
            "AWS": "AWS_MANAGED",
            "LOCAL": "CUSTOMER_MANAGED",
        }

        # Here, resourceType first partition (service) is case sensitive and
        # last partition (type) is case insensitive
        if resource_type and not any(
            permission["resourceType"].split(":")[0] == resource_type.split(":")[0]
            and permission["resourceType"].split(":")[-1].lower()
            == resource_type.split(":")[-1].lower()
            for permission in self.MANAGED_PERMISSIONS
        ):
            raise InvalidParameterException(f"Invalid resource type: {resource_type}")

        if resource_type:
            permissions = [
                permission
                for permission in self.MANAGED_PERMISSIONS
                if permission["resourceType"].split(":")[-1].lower()
                == resource_type.split(":")[-1].lower()
            ]
        else:
            permissions = self.MANAGED_PERMISSIONS

        if permission_type not in self.PERMISSION_TYPES:
            raise InvalidParameterException(
                f"{permission_type} is not a valid scope. Must be one of: "
                f"{', '.join(self.PERMISSION_TYPES)}."
            )

        if permission_type != "ALL":
            permissions = [
                permission
                for permission in permissions
                if permission_types_relation.get(permission_type)
                == permission["permissionType"]
            ]

        return dict(permissions=permissions)


ram_backends = BackendDict(ResourceAccessManagerBackend, "ram")
