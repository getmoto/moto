from collections import OrderedDict

from moto.core import CloudFormationModel
from .core import TaggedEC2Resource
from ..utils import (
    generic_filter,
    random_launch_template_id,
    utc_date_and_time,
    convert_tag_spec,
)
from ..exceptions import (
    InvalidLaunchTemplateNameAlreadyExistsError,
    InvalidLaunchTemplateNameNotFoundError,
    InvalidLaunchTemplateNameNotFoundWithNameError,
    MissingParameterError,
)


class LaunchTemplateVersion(object):
    def __init__(self, template, number, data, description):
        self.template = template
        self.number = number
        self.data = data
        self.description = description
        self.create_time = utc_date_and_time()

    @property
    def image_id(self):
        return self.data.get("ImageId", "")

    @property
    def instance_type(self):
        return self.data.get("InstanceType", "")

    @property
    def security_groups(self):
        return self.data.get("SecurityGroups", [])

    @property
    def user_data(self):
        return self.data.get("UserData", "")


class LaunchTemplate(TaggedEC2Resource, CloudFormationModel):
    def __init__(self, backend, name, template_data, version_description, tag_spec):
        self.ec2_backend = backend
        self.name = name
        self.id = random_launch_template_id()
        self.create_time = utc_date_and_time()
        tag_map = tag_spec.get("launch-template", {})
        self.add_tags(tag_map)
        self.tags = self.get_tags()

        self.versions = []
        self.create_version(template_data, version_description)
        self.default_version_number = 1

    def create_version(self, data, description):
        num = len(self.versions) + 1
        version = LaunchTemplateVersion(self, num, data, description)
        self.versions.append(version)
        return version

    def is_default(self, version):
        return self.default_version == version.number

    def get_version(self, num):
        if str(num).lower() == "$latest":
            return self.versions[-1]
        if str(num).lower() == "$default":
            return self.default_version()
        return self.versions[int(num) - 1]

    def default_version(self):
        return self.versions[self.default_version_number - 1]

    def latest_version(self):
        return self.versions[-1]

    @property
    def latest_version_number(self):
        return self.latest_version().number

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == "launch-template-name":
            return self.name
        else:
            return super().get_filter_value(filter_name, "DescribeLaunchTemplates")

    @staticmethod
    def cloudformation_name_type():
        return "LaunchTemplateName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-launchtemplate.html
        return "AWS::EC2::LaunchTemplate"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):

        from ..models import ec2_backends

        backend = ec2_backends[account_id][region_name]

        properties = cloudformation_json["Properties"]
        name = properties.get("LaunchTemplateName")
        data = properties.get("LaunchTemplateData")
        description = properties.get("VersionDescription")
        tag_spec = convert_tag_spec(
            properties.get("TagSpecifications", {}), tag_key="Tags"
        )

        launch_template = backend.create_launch_template(
            name, description, data, tag_spec
        )

        return launch_template

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):

        from ..models import ec2_backends

        backend = ec2_backends[account_id][region_name]

        properties = cloudformation_json["Properties"]

        name = properties.get("LaunchTemplateName")
        data = properties.get("LaunchTemplateData")
        description = properties.get("VersionDescription")

        launch_template = backend.get_launch_template_by_name(name)

        launch_template.create_version(data, description)

        return launch_template

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):

        from ..models import ec2_backends

        backend = ec2_backends[account_id][region_name]

        properties = cloudformation_json["Properties"]

        name = properties.get("LaunchTemplateName")

        backend.delete_launch_template(name, None)


class LaunchTemplateBackend:
    def __init__(self):
        self.launch_template_name_to_ids = {}
        self.launch_templates = OrderedDict()
        self.launch_template_insert_order = []

    def create_launch_template(self, name, description, template_data, tag_spec):
        if name in self.launch_template_name_to_ids:
            raise InvalidLaunchTemplateNameAlreadyExistsError()
        template = LaunchTemplate(self, name, template_data, description, tag_spec)
        self.launch_templates[template.id] = template
        self.launch_template_name_to_ids[template.name] = template.id
        self.launch_template_insert_order.append(template.id)
        return template

    def get_launch_template(self, template_id: str) -> LaunchTemplate:
        return self.launch_templates[template_id]

    def get_launch_template_by_name(self, name: str) -> LaunchTemplate:
        if name not in self.launch_template_name_to_ids:
            raise InvalidLaunchTemplateNameNotFoundWithNameError(name)
        return self.get_launch_template(self.launch_template_name_to_ids[name])

    def delete_launch_template(self, name, tid):
        if name:
            tid = self.launch_template_name_to_ids.get(name)
        if tid is None:
            raise MissingParameterError("launch template ID or launch template name")
        if tid not in self.launch_templates:
            raise InvalidLaunchTemplateNameNotFoundError()
        template = self.launch_templates.pop(tid)
        self.launch_template_name_to_ids.pop(template.name, None)
        return template

    def describe_launch_templates(
        self, template_names=None, template_ids=None, filters=None
    ):
        if template_names and not template_ids:
            template_ids = []
            for name in template_names:
                if name not in self.launch_template_name_to_ids:
                    raise InvalidLaunchTemplateNameNotFoundError()
                template_ids.append(self.launch_template_name_to_ids[name])

        if template_ids:
            templates = [
                self.launch_templates[tid]
                for tid in template_ids
                if tid in self.launch_templates
            ]
        else:
            templates = list(self.launch_templates.values())

        return generic_filter(filters, templates)
