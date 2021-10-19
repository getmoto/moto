from builtins import str

import json
import re

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID
from .exceptions import BadRequestException


class FakeResourceGroup(BaseModel):
    def __init__(
        self, name, resource_query, description=None, tags=None, configuration=None
    ):
        self.errors = []
        description = description or ""
        tags = tags or {}
        if self._validate_description(value=description):
            self._description = description
        if self._validate_name(value=name):
            self._name = name
        if self._validate_resource_query(value=resource_query):
            self._resource_query = resource_query
        if self._validate_tags(value=tags):
            self._tags = tags
        self._raise_errors()
        self.arn = "arn:aws:resource-groups:us-west-1:{AccountId}:{name}".format(
            name=name, AccountId=ACCOUNT_ID
        )
        self.configuration = configuration

    @staticmethod
    def _format_error(key, value, constraint):
        return "Value '{value}' at '{key}' failed to satisfy constraint: {constraint}".format(
            constraint=constraint, key=key, value=value
        )

    def _raise_errors(self):
        if self.errors:
            errors_len = len(self.errors)
            plural = "s" if len(self.errors) > 1 else ""
            errors = "; ".join(self.errors)
            raise BadRequestException(
                "{errors_len} validation error{plural} detected: {errors}".format(
                    errors_len=errors_len, plural=plural, errors=errors
                )
            )

    def _validate_description(self, value):
        errors = []
        if len(value) > 511:
            errors.append(
                self._format_error(
                    key="description",
                    value=value,
                    constraint="Member must have length less than or equal to 512",
                )
            )
        if not re.match(r"^[\sa-zA-Z0-9_.-]*$", value):
            errors.append(
                self._format_error(
                    key="name",
                    value=value,
                    constraint=r"Member must satisfy regular expression pattern: [\sa-zA-Z0-9_\.-]*",
                )
            )
        if errors:
            self.errors += errors
            return False
        return True

    def _validate_name(self, value):
        errors = []
        if len(value) > 128:
            errors.append(
                self._format_error(
                    key="name",
                    value=value,
                    constraint="Member must have length less than or equal to 128",
                )
            )
        # Note \ is a character to match not an escape.
        if not re.match(r"^[a-zA-Z0-9_\\.-]+$", value):
            errors.append(
                self._format_error(
                    key="name",
                    value=value,
                    constraint=r"Member must satisfy regular expression pattern: [a-zA-Z0-9_\.-]+",
                )
            )
        if errors:
            self.errors += errors
            return False
        return True

    def _validate_resource_query(self, value):
        if not value:
            return True
        errors = []
        if value["Type"] not in {"CLOUDFORMATION_STACK_1_0", "TAG_FILTERS_1_0"}:
            errors.append(
                self._format_error(
                    key="resourceQuery.type",
                    value=value,
                    constraint="Member must satisfy enum value set: [CLOUDFORMATION_STACK_1_0, TAG_FILTERS_1_0]",
                )
            )
        if len(value["Query"]) > 2048:
            errors.append(
                self._format_error(
                    key="resourceQuery.query",
                    value=value,
                    constraint="Member must have length less than or equal to 2048",
                )
            )
        if errors:
            self.errors += errors
            return False
        return True

    def _validate_tags(self, value):
        errors = []
        # AWS only outputs one error for all keys and one for all values.
        error_keys = None
        error_values = None
        regex = re.compile(r"^([\\p{L}\\p{Z}\\p{N}_.:/=+\-@]*)$")
        for tag_key, tag_value in value.items():
            # Validation for len(tag_key) >= 1 is done by botocore.
            if len(tag_key) > 128 or re.match(regex, tag_key):
                error_keys = self._format_error(
                    key="tags",
                    value=value,
                    constraint=(
                        "Map value must satisfy constraint: ["
                        "Member must have length less than or equal to 128, "
                        "Member must have length greater than or equal to 1, "
                        r"Member must satisfy regular expression pattern: ^([\p{L}\p{Z}\p{N}_.:/=+\-@]*)$"
                        "]"
                    ),
                )
            # Validation for len(tag_value) >= 0 is nonsensical.
            if len(tag_value) > 256 or re.match(regex, tag_key):
                error_values = self._format_error(
                    key="tags",
                    value=value,
                    constraint=(
                        "Map value must satisfy constraint: ["
                        "Member must have length less than or equal to 256, "
                        "Member must have length greater than or equal to 0, "
                        r"Member must satisfy regular expression pattern: ^([\p{L}\p{Z}\p{N}_.:/=+\-@]*)$"
                        "]"
                    ),
                )
        if error_keys:
            errors.append(error_keys)
        if error_values:
            errors.append(error_values)
        if errors:
            self.errors += errors
            return False
        return True

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        if not self._validate_description(value=value):
            self._raise_errors()
        self._description = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not self._validate_name(value=value):
            self._raise_errors()
        self._name = value

    @property
    def resource_query(self):
        return self._resource_query

    @resource_query.setter
    def resource_query(self, value):
        if not self._validate_resource_query(value=value):
            self._raise_errors()
        self._resource_query = value

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, value):
        if not self._validate_tags(value=value):
            self._raise_errors()
        self._tags = value


class ResourceGroups:
    def __init__(self):
        self.by_name = {}
        self.by_arn = {}

    def __contains__(self, item):
        return item in self.by_name

    def append(self, resource_group):
        self.by_name[resource_group.name] = resource_group
        self.by_arn[resource_group.arn] = resource_group

    def delete(self, name):
        group = self.by_name[name]
        del self.by_name[name]
        del self.by_arn[group.arn]
        return group


class ResourceGroupsBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(ResourceGroupsBackend, self).__init__()
        self.region_name = region_name
        self.groups = ResourceGroups()

    @staticmethod
    def _validate_resource_query(resource_query):
        if not resource_query:
            return
        type = resource_query["Type"]
        query = json.loads(resource_query["Query"])
        query_keys = set(query.keys())
        invalid_json_exception = BadRequestException(
            "Invalid query: Invalid query format: check JSON syntax"
        )
        if not isinstance(query["ResourceTypeFilters"], list):
            raise invalid_json_exception
        if type == "CLOUDFORMATION_STACK_1_0":
            if query_keys != {"ResourceTypeFilters", "StackIdentifier"}:
                raise invalid_json_exception
            stack_identifier = query["StackIdentifier"]
            if not isinstance(stack_identifier, str):
                raise invalid_json_exception
            if not re.match(
                r"^arn:aws:cloudformation:[a-z]{2}-[a-z]+-[0-9]+:[0-9]+:stack/[-0-9A-z]+/[-0-9a-f]+$",
                stack_identifier,
            ):
                raise BadRequestException(
                    "Invalid query: Verify that the specified ARN is formatted correctly."
                )
            # Once checking other resources is implemented.
            # if stack_identifier not in self.cloudformation_backend.stacks:
            #   raise BadRequestException("Invalid query: The specified CloudFormation stack doesn't exist.")
        if type == "TAG_FILTERS_1_0":
            if query_keys != {"ResourceTypeFilters", "TagFilters"}:
                raise invalid_json_exception
            tag_filters = query["TagFilters"]
            if not isinstance(tag_filters, list):
                raise invalid_json_exception
            if not tag_filters or len(tag_filters) > 50:
                raise BadRequestException(
                    "Invalid query: The TagFilters list must contain between 1 and 50 elements"
                )
            for tag_filter in tag_filters:
                if not isinstance(tag_filter, dict):
                    raise invalid_json_exception
                if set(tag_filter.keys()) != {"Key", "Values"}:
                    raise invalid_json_exception
                key = tag_filter["Key"]
                if not isinstance(key, str):
                    raise invalid_json_exception
                if not key:
                    raise BadRequestException(
                        "Invalid query: The TagFilter element cannot have empty or null Key field"
                    )
                if len(key) > 128:
                    raise BadRequestException(
                        "Invalid query: The maximum length for a tag Key is 128"
                    )
                values = tag_filter["Values"]
                if not isinstance(values, list):
                    raise invalid_json_exception
                if len(values) > 20:
                    raise BadRequestException(
                        "Invalid query: The TagFilter Values list must contain between 0 and 20 elements"
                    )
                for value in values:
                    if not isinstance(value, str):
                        raise invalid_json_exception
                    if len(value) > 256:
                        raise BadRequestException(
                            "Invalid query: The maximum length for a tag Value is 256"
                        )

    @staticmethod
    def _validate_tags(tags):
        for tag in tags:
            if tag.lower().startswith("aws:"):
                raise BadRequestException("Tag keys must not start with 'aws:'")

    def create_group(
        self, name, resource_query, description=None, tags=None, configuration=None
    ):
        tags = tags or {}
        group = FakeResourceGroup(
            name=name,
            resource_query=resource_query,
            description=description,
            tags=tags,
            configuration=configuration,
        )
        if name in self.groups:
            raise BadRequestException("Cannot create group: group already exists")
        if name.upper().startswith("AWS"):
            raise BadRequestException("Group name must not start with 'AWS'")
        self._validate_tags(tags)
        self._validate_resource_query(resource_query)
        self.groups.append(group)
        return group

    def delete_group(self, group_name):
        return self.groups.delete(name=group_name)

    def get_group(self, group_name):
        return self.groups.by_name[group_name]

    def get_tags(self, arn):
        return self.groups.by_arn[arn].tags

    # def list_group_resources(self):
    #     ...

    def list_groups(self, filters=None, max_results=None, next_token=None):
        return self.groups.by_name

    # def search_resources(self):
    #     ...

    def tag(self, arn, tags):
        all_tags = self.groups.by_arn[arn].tags
        all_tags.update(tags)
        self._validate_tags(all_tags)
        self.groups.by_arn[arn].tags = all_tags

    def untag(self, arn, keys):
        group = self.groups.by_arn[arn]
        for key in keys:
            del group.tags[key]

    def update_group(self, group_name, description=None):
        if description:
            self.groups.by_name[group_name].description = description
        return self.groups.by_name[group_name]

    def update_group_query(self, group_name, resource_query):
        self._validate_resource_query(resource_query)
        self.groups.by_name[group_name].resource_query = resource_query
        return self.groups.by_name[group_name]

    def get_group_configuration(self, group_name):
        group = self.groups.by_name.get(group_name)
        configuration = group.configuration
        return configuration

    def put_group_configuration(self, group_name, configuration):
        self.groups.by_name[group_name].configuration = configuration
        return self.groups.by_name[group_name]


resourcegroups_backends = {}
for region in Session().get_available_regions("resource-groups"):
    resourcegroups_backends[region] = ResourceGroupsBackend(region)
for region in Session().get_available_regions(
    "resource-groups", partition_name="aws-us-gov"
):
    resourcegroups_backends[region] = ResourceGroupsBackend(region)
for region in Session().get_available_regions(
    "resource-groups", partition_name="aws-cn"
):
    resourcegroups_backends[region] = ResourceGroupsBackend(region)
