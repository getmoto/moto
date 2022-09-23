from moto.ec2.exceptions import FilterNotImplementedError
from moto.moto_api._internal import mock_random
from ._base_response import EC2BaseResponse

from xml.etree import ElementTree
from xml.dom import minidom


def xml_root(name):
    root = ElementTree.Element(
        name, {"xmlns": "http://ec2.amazonaws.com/doc/2016-11-15/"}
    )
    request_id = str(mock_random.uuid4()) + "example"
    ElementTree.SubElement(root, "requestId").text = request_id

    return root


def xml_serialize(tree, key, value):
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
            'Don\'t know how to serialize "{}" to xml'.format(value.__class__)
        )


def pretty_xml(tree):
    rough = ElementTree.tostring(tree, "utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="    ")


def parse_object(raw_data):
    out_data = {}
    for key, value in raw_data.items():
        key_fix_splits = key.split("_")
        key_len = len(key_fix_splits)

        new_key = ""
        for i in range(0, key_len):
            new_key += key_fix_splits[i][0].upper() + key_fix_splits[i][1:]

        data = out_data
        splits = new_key.split(".")
        for split in splits[:-1]:
            if split not in data:
                data[split] = {}
            data = data[split]

        data[splits[-1]] = value

    out_data = parse_lists(out_data)
    return out_data


def parse_lists(data):
    for key, value in data.items():
        if isinstance(value, dict):
            keys = data[key].keys()
            is_list = all(map(lambda k: k.isnumeric(), keys))

            if is_list:
                new_value = []
                keys = sorted(list(keys))
                for k in keys:
                    lvalue = value[k]
                    if isinstance(lvalue, dict):
                        lvalue = parse_lists(lvalue)
                    new_value.append(lvalue)
                data[key] = new_value
    return data


class LaunchTemplates(EC2BaseResponse):
    def create_launch_template(self):
        name = self._get_param("LaunchTemplateName")
        version_description = self._get_param("VersionDescription")
        tag_spec = self._parse_tag_specification()

        raw_template_data = self._get_dict_param("LaunchTemplateData.")
        parsed_template_data = parse_object(raw_template_data)

        if self.is_not_dryrun("CreateLaunchTemplate"):
            if tag_spec:
                if "TagSpecifications" not in parsed_template_data:
                    parsed_template_data["TagSpecifications"] = []
                converted_tag_spec = []
                for resource_type, tags in tag_spec.items():
                    converted_tag_spec.append(
                        {
                            "ResourceType": resource_type,
                            "Tags": [
                                {"Key": key, "Value": value}
                                for key, value in tags.items()
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

    def create_launch_template_version(self):
        name = self._get_param("LaunchTemplateName")
        tmpl_id = self._get_param("LaunchTemplateId")
        if name:
            template = self.ec2_backend.get_launch_template_by_name(name)
        if tmpl_id:
            template = self.ec2_backend.get_launch_template(tmpl_id)

        version_description = self._get_param("VersionDescription")

        raw_template_data = self._get_dict_param("LaunchTemplateData.")
        template_data = parse_object(raw_template_data)

        if self.is_not_dryrun("CreateLaunchTemplate"):
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

    def delete_launch_template(self):
        name = self._get_param("LaunchTemplateName")
        tid = self._get_param("LaunchTemplateId")

        if self.is_not_dryrun("DeleteLaunchTemplate"):
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

    # def delete_launch_template_versions(self):
    #     pass

    def describe_launch_template_versions(self):
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

        if self.is_not_dryrun("DescribeLaunchTemplateVersions"):
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
                    ret_versions.append(template.get_version(int(v)))
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

    def describe_launch_templates(self):
        max_results = self._get_int_param("MaxResults", 15)
        template_names = self._get_multi_param("LaunchTemplateName")
        template_ids = self._get_multi_param("LaunchTemplateId")
        filters = self._filters_from_querystring()

        if self.is_not_dryrun("DescribeLaunchTemplates"):
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

    # def modify_launch_template(self):
    #     pass
