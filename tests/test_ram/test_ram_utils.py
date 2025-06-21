import re

from moto.ram.utils import (
    AWS_MANAGED_PERMISSIONS,
    RAM_RESOURCE_TYPES,
    format_ram_permission,
)


def test_format_ram_permission_defaults():
    name = "TestPermission"
    resource_type = "test:Resource"
    result = format_ram_permission(name, resource_type)
    assert result["name"] == name
    assert result["resourceType"] == resource_type
    assert result["version"] == "1"
    assert result["arn"] == f"arn:aws:ram::aws:permission/{name}"
    assert result["status"] == "ATTACHABLE"
    assert result["isResourceTypeDefault"] is True
    assert result["permissionType"] == "AWS_MANAGED"
    assert result["defaultVersion"] is True
    # creationTime and lastUpdatedTime should be a string in the expected format
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}", result["creationTime"]
    )
    assert result["creationTime"] == result["lastUpdatedTime"]


def test_format_ram_permission_custom_values():
    name = "CustomPermission"
    resource_type = "custom:Type"
    version = "2"
    arn_prefix = "arn:aws:ram::custom:permission/"
    status = "UNATTACHABLE"
    creation_time = "2023-01-01 12:00:00.000"
    last_updated_time = "2023-01-02 13:00:00.000"
    is_resource_type_default = False
    permission_type = "CUSTOM"
    default_version = False

    result = format_ram_permission(
        name=name,
        resource_type=resource_type,
        version=version,
        arn_prefix=arn_prefix,
        status=status,
        creation_time=creation_time,
        last_updated_time=last_updated_time,
        is_resource_type_default=is_resource_type_default,
        permission_type=permission_type,
        default_version=default_version,
    )
    assert result["name"] == name
    assert result["resourceType"] == resource_type
    assert result["version"] == version
    assert result["arn"] == f"{arn_prefix}{name}"
    assert result["status"] == status
    assert result["creationTime"] == creation_time
    assert result["lastUpdatedTime"] == last_updated_time
    assert result["isResourceTypeDefault"] is False
    assert result["permissionType"] == permission_type
    assert result["defaultVersion"] is False


def test_ram_resource_types_structure():
    for entry in RAM_RESOURCE_TYPES:
        assert "resourceType" in entry
        assert "serviceName" in entry
        assert "resourceRegionScope" in entry
        assert entry["resourceRegionScope"] in ("REGIONAL", "GLOBAL")


def test_aws_managed_permissions_structure():
    for perm in AWS_MANAGED_PERMISSIONS:
        assert "arn" in perm
        assert perm["arn"].startswith("arn:aws:ram::aws:permission/")
        assert "name" in perm
        assert "resourceType" in perm
        assert "creationTime" in perm
        assert "lastUpdatedTime" in perm
        assert "status" in perm
        assert "permissionType" in perm
        assert perm["permissionType"] == "AWS_MANAGED"
        assert isinstance(perm["isResourceTypeDefault"], bool)
