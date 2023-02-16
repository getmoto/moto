from typing import Any
from moto.ec2.exceptions import FilterNotImplementedError
from moto.moto_api._internal import mock_random
from ._base_response import EC2BaseResponse

from xml.etree import ElementTree
from xml.dom import minidom


def xml_root(name: str) -> ElementTree.Element:
    root = ElementTree.Element(
        name, {"xmlns": "http://ec2.amazonaws.com/doc/2016-11-15/"}
    )
    request_id = str(mock_random.uuid4()) + "example"
    ElementTree.SubElement(root, "requestId").text = request_id

    return root


def xml_serialize(tree: ElementTree.Element, key: str, value: Any) -> None:
    name = key[0].lower() + key[1:]
    if isinstance(value, list):
        if name[-1] == "s":
            name = name[:-1]

        name = name + "Set"

    node = ElementTree.SubElement(tree, name)

    if isinstance(value, (str, int, float, str)):
        node.text = str(value)
    elif isinstance(value, dict):
        for dictkey, dictvalue in value.items():
            xml_serialize(node, dictkey, dictvalue)
    elif isinstance(value, list):
        for item in value:
            xml_serialize(node, "item", item)
    elif value is None:
        pass
    else:
        raise NotImplementedError(
            f'Don\'t know how to serialize "{value.__class__}" to xml'
        )


def pretty_xml(tree: ElementTree.Element) -> str:
    rough = ElementTree.tostring(tree, "utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="    ")


class LaunchTemplates(EC2BaseResponse):
    def create_launch_template(self) -> str:
        name = self._get_param("LaunchTemplateName")
        version_description = self._get_param("VersionDescription")
        tag_spec = self._parse_tag_specification()

        parsed_template_data = self._get_multi_param_dict("LaunchTemplateData")

        self.error_on_dryrun()

        if tag_spec:
            if "TagSpecifications" not in parsed_template_data:
                parsed_template_data["TagSpecifications"] = []
            converted_tag_spec = []
            for resource_type, tags in tag_spec.items():
                converted_tag_spec.append(
                    {
                        "ResourceType": resource_type,
                        "Tags": [
                            {"Key": key, "Value": value} for key, value in tags.items()
                        ],
                    }
                )

            parsed_template_data["TagSpecifications"].extend(converted_tag_spec)

        template = self.ec2_backend.create_launch_template(
            name, version_description, parsed_template_data, tag_spec
        )
        version = template.default_version()

        tree = xml_root("CreateLaunchTemplateResponse")
        xml_serialize(
            tree,
            "launchTemplate",
            {
                "createTime": version.create_time,
                "createdBy": f"arn:aws:iam::{self.current_account}:root",
                "defaultVersionNumber": template.default_version_number,
                "latestVersionNumber": version.number,
                "launchTemplateId": template.id,
                "launchTemplateName": template.name,
                "tags": template.tags,
            },
        )

        return pretty_xml(tree)

    def create_launch_template_version(self) -> str:
        name = self._get_param("LaunchTemplateName")
        tmpl_id = self._get_param("LaunchTemplateId")
        if name:
            template = self.ec2_backend.get_launch_template_by_name(name)
        if tmpl_id:
            template = self.ec2_backend.get_launch_template(tmpl_id)

        version_description = self._get_param("VersionDescription")

        template_data = self._get_multi_param_dict("LaunchTemplateData")

        self.error_on_dryrun()

        version = template.create_version(template_data, version_description)

        tree = xml_root("CreateLaunchTemplateVersionResponse")
        xml_serialize(
            tree,
            "launchTemplateVersion",
            {
                "createTime": version.create_time,
                "createdBy": f"arn:aws:iam::{self.current_account}:root",
                "defaultVersion": template.is_default(version),
                "launchTemplateData": version.data,
                "launchTemplateId": template.id,
                "launchTemplateName": template.name,
                "versionDescription": version.description,
                "versionNumber": version.number,
            },
        )
        return pretty_xml(tree)

    def delete_launch_template(self) -> str:
        name = self._get_param("LaunchTemplateName")
        tid = self._get_param("LaunchTemplateId")

        self.error_on_dryrun()

        template = self.ec2_backend.delete_launch_template(name, tid)

        tree = xml_root("DeleteLaunchTemplatesResponse")
        xml_serialize(
            tree,
            "launchTemplate",
            {
                "defaultVersionNumber": template.default_version_number,
                "launchTemplateId": template.id,
                "launchTemplateName": template.name,
            },
        )

        return pretty_xml(tree)

    def describe_launch_template_versions(self) -> str:
        name = self._get_param("LaunchTemplateName")
        template_id = self._get_param("LaunchTemplateId")
        if name:
            template = self.ec2_backend.get_launch_template_by_name(name)
        if template_id:
            template = self.ec2_backend.get_launch_template(template_id)

        max_results = self._get_int_param("MaxResults", 15)
        versions = self._get_multi_param("LaunchTemplateVersion")
        min_version = self._get_int_param("MinVersion")
        max_version = self._get_int_param("MaxVersion")

        filters = self._filters_from_querystring()
        if filters:
            raise FilterNotImplementedError(
                "all filters", "DescribeLaunchTemplateVersions"
            )

        self.error_on_dryrun()

        tree = ElementTree.Element(
            "DescribeLaunchTemplateVersionsResponse",
            {"xmlns": "http://ec2.amazonaws.com/doc/2016-11-15/"},
        )
        request_id = ElementTree.SubElement(tree, "requestId")
        request_id.text = "65cadec1-b364-4354-8ca8-4176dexample"

        versions_node = ElementTree.SubElement(tree, "launchTemplateVersionSet")

        ret_versions = []
        if versions:
            for v in versions:
                if str(v).lower() == "$latest" or "$default":
                    tv = template.get_version(v)
                else:
                    tv = template.get_version(int(v))
                ret_versions.append(tv)
        elif min_version:
            if max_version:
                vMax = max_version
            else:
                vMax = min_version + max_results

            vMin = min_version - 1
            ret_versions = template.versions[vMin:vMax]
        elif max_version:
            vMax = max_version
            ret_versions = template.versions[:vMax]
        else:
            ret_versions = template.versions

        ret_versions = ret_versions[:max_results]

        for version in ret_versions:
            xml_serialize(
                versions_node,
                "item",
                {
                    "createTime": version.create_time,
                    "createdBy": f"arn:aws:iam::{self.current_account}:root",
                    "defaultVersion": True,
                    "launchTemplateData": version.data,
                    "launchTemplateId": template.id,
                    "launchTemplateName": template.name,
                    "versionDescription": version.description,
                    "versionNumber": version.number,
                },
            )

        return pretty_xml(tree)

    def describe_launch_templates(self) -> str:
        max_results = self._get_int_param("MaxResults", 15)
        template_names = self._get_multi_param("LaunchTemplateName")
        template_ids = self._get_multi_param("LaunchTemplateId")
        filters = self._filters_from_querystring()

        self.error_on_dryrun()

        tree = ElementTree.Element("DescribeLaunchTemplatesResponse")
        templates_node = ElementTree.SubElement(tree, "launchTemplates")

        templates = self.ec2_backend.describe_launch_templates(
            template_names=template_names,
            template_ids=template_ids,
            filters=filters,
        )

        templates = templates[:max_results]

        for template in templates:
            xml_serialize(
                templates_node,
                "item",
                {
                    "createTime": template.create_time,
                    "createdBy": f"arn:aws:iam::{self.current_account}:root",
                    "defaultVersionNumber": template.default_version_number,
                    "latestVersionNumber": template.latest_version_number,
                    "launchTemplateId": template.id,
                    "launchTemplateName": template.name,
                    "tags": template.tags,
                },
            )

        return pretty_xml(tree)
