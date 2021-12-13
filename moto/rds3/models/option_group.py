from __future__ import unicode_literals

from moto.compat import OrderedDict
from .base import BaseRDSBackend, BaseRDSModel
from .tag import TaggableRDSResource
from .. import utils
from ..exceptions import (
    InvalidParameterCombination,
    InvalidParameterValue,
    OptionGroupAlreadyExists,
    OptionGroupNotFound,
)


class OptionGroupOptionSetting(object):
    def __init__(self, **kwargs):
        self.allowed_values = kwargs.get("allowed_values")
        self.apply_type = kwargs.get("apply_type")
        self.default_value = kwargs.get("default_value")
        self.is_modifiable = kwargs.get("is_modifiable")
        self.setting_description = kwargs.get("setting_description")
        self.setting_name = kwargs.get("setting_name")


class OptionGroupOption(object):
    def __init__(self, **kwargs):
        self.default_port = kwargs.get("default_port")
        self.description = kwargs.get("description")
        self.engine_name = kwargs.get("engine_name")
        self.major_engine_version = kwargs.get("major_engine_version")
        self.minimum_required_minor_engine_version = kwargs.get(
            "minimum_required_minor_engine_version"
        )
        self.name = kwargs.get("name")
        self.option_group_option_settings = self._make_option_group_option_settings(
            kwargs.get("option_group_option_settings", [])
        )
        self.options_conflicts_with = kwargs.get("options_conflicts_with", [])
        self.options_depended_on = kwargs.get("options_depended_on", [])
        self.permanent = kwargs.get("permanent")
        self.persistent = kwargs.get("persistent")
        self.port_required = kwargs.get("port_required")
        self.requires_auto_minor_engine_version_upgrade = kwargs.get(
            "requires_auto_minor_engine_version_upgrade"
        )
        self.vpc_only = kwargs.get("vpc_only")

    @property
    def resource_id(self):
        return "{}-{}-{}".format(self.engine_name, self.major_engine_version, self.name)

    @staticmethod
    def _make_option_group_option_settings(option_group_option_settings_kwargs):
        return [
            OptionGroupOptionSetting(**setting_kwargs)
            for setting_kwargs in option_group_option_settings_kwargs
        ]


class OptionGroup(TaggableRDSResource, BaseRDSModel):

    resource_type = "og"

    def __init__(
        self,
        backend,
        option_group_name,
        option_group_description,
        engine_name,
        major_engine_version,
        tags=None,
    ):
        super(OptionGroup, self).__init__(backend)
        self.engine_name = engine_name
        self.major_engine_version = major_engine_version
        self.option_group_description = option_group_description
        self.option_group_name = option_group_name
        self.allows_vpc_and_non_vpc_instance_memberships = False
        self.options = []
        self.vpc_id = "null"
        if tags:
            self.add_tags(tags)

    @property
    def resource_id(self):
        return self.option_group_name

    @property
    def name(self):
        return self.option_group_name

    @property
    def option_group_arn(self):
        return self.arn

    def remove_options(self, options_to_remove):
        # TODO: Check for option in self.options and remove if exists.
        # Raise error otherwise
        return self

    def add_options(self, options_to_add):
        # TODO: Validate option and add it to self.options.
        # If invalid raise error
        return self


class OptionGroupBackend(BaseRDSBackend):
    def __init__(self):
        super(OptionGroupBackend, self).__init__()
        self.option_groups = OrderedDict()
        self.option_group_options = OrderedDict()
        for og in utils.default_option_groups:
            option_group = OptionGroup(
                backend=self,
                option_group_name=og["OptionGroupName"],
                engine_name=og["EngineName"],
                major_engine_version=og["MajorEngineVersion"],
                option_group_description=og["OptionGroupDescription"],
            )
            self.option_groups[option_group.resource_id] = option_group
        for ogo in utils.option_group_options:
            option_group_option = OptionGroupOption(
                default_port=ogo.get("DefaultPort"),
                description=ogo.get("Description"),
                engine_name=ogo.get("EngineName"),
                major_engine_version=ogo.get("MajorEngineVersion"),
                minimum_required_minor_engine_version=ogo.get(
                    "MinimumRequiredMinorEngineVersion"
                ),
                name=ogo.get("Name"),
                option_group_option_settings=ogo.get("OptionGroupOptionSettings"),
                options_conflicts_with=ogo.get("OptionsConflictsWith"),
                options_depended_on=ogo.get("OptionsDependedOn"),
                permanent=ogo.get("Permanent"),
                persistent=ogo.get("Persistent"),
                port_required=ogo.get("PortRequired"),
                requires_auto_minor_engine_version_upgrade=ogo.get(
                    "RequiresAutoMinorEngineVersionUpgrade"
                ),
                vpc_only=ogo.get("VpcOnly"),
            )
            self.option_group_options[
                option_group_option.resource_id
            ] = option_group_option

    def get_option_group(self, option_group_name):
        if option_group_name not in self.option_groups:
            raise OptionGroupNotFound(option_group_name)
        return self.option_groups[option_group_name]

    def create_option_group(
        self,
        option_group_name,
        option_group_description="",
        engine_name=None,
        major_engine_version=None,
        **kwargs
    ):
        valid_option_group_engines = {
            "mysql": ["5.6"],
            "oracle-se1": ["11.2"],
            "oracle-se2": ["12.1"],
            "oracle-se": ["11.2"],
            "oracle-ee": ["11.2"],
            "sqlserver-se": ["10.50", "11.00"],
            "sqlserver-ee": ["10.50", "11.00"],
        }
        if option_group_name in self.option_groups:
            raise OptionGroupAlreadyExists(option_group_name)
        if not option_group_description:
            raise InvalidParameterValue(
                "The parameter OptionGroupDescription must be provided and must not be blank."
            )
        if engine_name not in valid_option_group_engines.keys():
            raise InvalidParameterValue("Invalid DB engine: non-existent")
        if major_engine_version not in valid_option_group_engines[engine_name]:
            raise InvalidParameterCombination(
                "Cannot find major version {0} for {1}".format(
                    major_engine_version, engine_name
                )
            )
        option_group = OptionGroup(
            backend=self,
            option_group_name=option_group_name,
            option_group_description=option_group_description,
            engine_name=engine_name,
            major_engine_version=major_engine_version,
            **kwargs
        )
        self.option_groups[option_group_name] = option_group
        return option_group

    def delete_option_group(self, option_group_name):
        option_group = self.get_option_group(option_group_name)
        return self.option_groups.pop(option_group.resource_id)

    def describe_option_groups(
        self,
        option_group_name=None,
        engine_name=None,
        major_engine_version=None,
        **kwargs
    ):
        if option_group_name:
            return [self.get_option_group(option_group_name)]
        option_group_list = []
        for name, group in self.option_groups.items():
            if engine_name and group.engine_name != engine_name:
                continue
            elif (
                major_engine_version
                and group.major_engine_version != major_engine_version
            ):
                continue
            else:
                option_group_list.append(group)
        return option_group_list

    def describe_option_group_options(
        self, engine_name, major_engine_version=None, **kwargs
    ):
        option_group_options = [ogo for ogo in self.option_group_options.values()]
        if engine_name not in utils.VALID_DB_ENGINES:
            raise InvalidParameterValue("Invalid DB engine")
        option_group_options = [
            ogo for ogo in option_group_options if ogo.engine_name == engine_name
        ]
        if major_engine_version:
            if major_engine_version not in set(
                [ogo.major_engine_version for ogo in option_group_options]
            ):
                msg = "Cannot find major version {} for {}".format(
                    major_engine_version, engine_name
                )
                raise InvalidParameterCombination(msg)
            option_group_options = [
                ogo
                for ogo in option_group_options
                if ogo.major_engine_version == major_engine_version
            ]
        return option_group_options

    def modify_option_group(
        self,
        option_group_name,
        options_to_include=None,
        options_to_remove=None,
        apply_immediately=None,
    ):
        option_group = self.get_option_group(option_group_name)
        if not options_to_include and not options_to_remove:
            raise InvalidParameterValue(
                "At least one option must be added, modified, or removed."
            )
        if options_to_remove:
            option_group.remove_options(options_to_remove)
        if options_to_include:
            option_group.add_options(options_to_include)
        return option_group
