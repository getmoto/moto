from moto.core.responses import ActionResult
from moto.ec2.exceptions import FilterNotImplementedError
from moto.ec2.utils import parse_user_data

from ._base_response import EC2BaseResponse


class LaunchTemplates(EC2BaseResponse):
    def create_launch_template(self) -> ActionResult:
        name = self._get_param("LaunchTemplateName")
        version_description = self._get_param("VersionDescription")
        tag_spec = self._parse_tag_specification()

        parsed_template_data = self._get_param("LaunchTemplateData", {})
        parsed_template_data["UserData"] = parse_user_data(
            self._get_param("LaunchTemplateData.UserData")
        )
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

        result = {
            "LaunchTemplate": {
                "CreateTime": version.create_time,
                "CreatedBy": f"arn:{self.partition}:iam::{self.current_account}:root",
                "DefaultVersionNumber": template.default_version_number,
                "LatestVersionNumber": version.number,
                "LaunchTemplateId": template.id,
                "LaunchTemplateName": template.name,
                "Tags": template.tags,
            },
        }

        return ActionResult(result)

    def create_launch_template_version(self) -> ActionResult:
        name = self._get_param("LaunchTemplateName")
        tmpl_id = self._get_param("LaunchTemplateId")
        if name:
            template = self.ec2_backend.get_launch_template_by_name(name)
        if tmpl_id:
            template = self.ec2_backend.get_launch_template(tmpl_id)

        version_description = self._get_param("VersionDescription")

        template_data = self._get_param("LaunchTemplateData", {})

        self.error_on_dryrun()

        version = template.create_version(template_data, version_description)

        result = {
            "LaunchTemplateVersion": {
                "CreateTime": version.create_time,
                "CreatedBy": f"arn:{self.partition}:iam::{self.current_account}:root",
                "DefaultVersion": template.is_default(version),
                "LaunchTemplateData": version.data,
                "LaunchTemplateId": template.id,
                "LaunchTemplateName": template.name,
                "VersionDescription": version.description,
                "VersionNumber": version.number,
            },
        }
        return ActionResult(result)

    def delete_launch_template(self) -> ActionResult:
        name = self._get_param("LaunchTemplateName")
        tid = self._get_param("LaunchTemplateId")

        self.error_on_dryrun()

        template = self.ec2_backend.delete_launch_template(name, tid)

        result = {
            "LaunchTemplate": {
                "DefaultVersionNumber": template.default_version_number,
                "LaunchTemplateId": template.id,
                "LaunchTemplateName": template.name,
            },
        }

        return ActionResult(result)

    def describe_launch_template_versions(self) -> ActionResult:
        name = self._get_param("LaunchTemplateName")
        template_id = self._get_param("LaunchTemplateId")
        if name:
            template = self.ec2_backend.get_launch_template_by_name(name)
        elif template_id:
            template = self.ec2_backend.get_launch_template(template_id)
        else:
            template = None

        max_results = self._get_int_param("MaxResults", 15)
        versions = self._get_param("Versions", [])
        min_version = self._get_int_param("MinVersion")
        max_version = self._get_int_param("MaxVersion")

        filters = self._filters_from_querystring()
        if filters:
            raise FilterNotImplementedError(
                "all filters", "DescribeLaunchTemplateVersions"
            )

        self.error_on_dryrun()

        ret_versions = []
        if versions and template is not None:
            for v in versions:
                ret_versions.append(template.get_version(v))
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
        elif template is not None:
            ret_versions = template.versions

        ret_versions = ret_versions[:max_results]

        result = {
            "LaunchTemplateVersions": [
                {
                    "CreateTime": version.create_time,
                    "CreatedBy": f"arn:{self.partition}:iam::{self.current_account}:root",
                    "DefaultVersion": True,
                    "LaunchTemplateData": version.data,
                    "LaunchTemplateId": template.id,
                    "LaunchTemplateName": template.name,
                    "VersionDescription": version.description,
                    "VersionNumber": version.number,
                }
                for version in ret_versions
            ]
        }

        return ActionResult(result)

    def describe_launch_templates(self) -> ActionResult:
        max_results = self._get_int_param("MaxResults", 15)
        template_names = self._get_param("LaunchTemplateNames", [])
        template_ids = self._get_param("LaunchTemplateIds", [])
        filters = self._filters_from_querystring()

        self.error_on_dryrun()

        templates = self.ec2_backend.describe_launch_templates(
            template_names=template_names,
            template_ids=template_ids,
            filters=filters,
        )

        templates = templates[:max_results]

        result = {
            "LaunchTemplates": [
                {
                    "CreateTime": template.create_time,
                    "CreatedBy": f"arn:{self.partition}:iam::{self.current_account}:root",
                    "DefaultVersionNumber": template.default_version_number,
                    "LatestVersionNumber": template.latest_version_number,
                    "LaunchTemplateId": template.id,
                    "LaunchTemplateName": template.name,
                    "Tags": template.tags,
                }
                for template in templates
            ]
        }

        return ActionResult(result)

    def get_launch_template_data(self) -> str:
        instance_id = self._get_param("InstanceId")
        instance = self.ec2_backend.get_launch_template_data(instance_id)
        template = self.response_template(GET_LAUNCH_TEMPLATE_DATA_RESPONSE)
        return template.render(i=instance)

    def modify_launch_template(self) -> ActionResult:
        template_name = self._get_param("LaunchTemplateName")
        template_id = self._get_param("LaunchTemplateId")
        default_version = self._get_param("DefaultVersion")

        self.error_on_dryrun()

        template = self.ec2_backend.modify_launch_template(
            template_name=template_name,
            template_id=template_id,
            default_version=default_version,
        )

        result = {
            "LaunchTemplate": {
                "CreateTime": template.create_time,
                "CreatedBy": f"arn:{self.partition}:iam::{self.current_account}:root",
                "DefaultVersionNumber": template.default_version_number,
                "LatestVersionNumber": template.latest_version_number,
                "LaunchTemplateId": template.id,
                "LaunchTemplateName": template.name,
                "Tags": template.tags,
            },
        }
        return ActionResult(result)


GET_LAUNCH_TEMPLATE_DATA_RESPONSE = """<GetLaunchTemplateDataResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>801986a5-0ee2-46bd-be02-abcde1234567</requestId>
    <launchTemplateData>
        <blockDeviceMappingSet>
        {% for device_name, device in i.block_device_mapping.items() %}
            <item>
                <deviceName>{{ device_name }}</deviceName>
                <ebs>
                    <deleteOnTermination>{{ device.delete_on_termination }}</deleteOnTermination>
                    <encrypted>{{ device.encrypted }}</encrypted>
                    <snapshotId>{{ device.snapshot_id }}</snapshotId>
                    <volumeSize>{{ device.size }}</volumeSize>
                    <volumeType>{{ device.volume_type }}</volumeType>
                </ebs>
            </item>
        {% endfor %}
        </blockDeviceMappingSet>
        <capacityReservationSpecification>
            <capacityReservationPreference>open</capacityReservationPreference>
        </capacityReservationSpecification>
        <creditSpecification>
            <cpuCredits>standard</cpuCredits>
        </creditSpecification>
        <disableApiStop>{{ i.disable_api_stop }}</disableApiStop>
        <disableApiTermination>{{ i.disable_api_termination }}</disableApiTermination>
        <ebsOptimized>{{ i.ebs_optimised }}</ebsOptimized>
        <enclaveOptions>
            <enabled>false</enabled>
        </enclaveOptions>
        <hibernationOptions>
            <configured>false</configured>
        </hibernationOptions>
        <imageId>{{ i.image_id }}</imageId>
        <instanceInitiatedShutdownBehavior>{{ i.instance_initiated_shutdown_behavior }}</instanceInitiatedShutdownBehavior>
        <instanceType>{{ i.instance_type }}</instanceType>
        <keyName>{{ i.key_name }}</keyName>
        <maintenanceOptions>
            <autoRecovery>default</autoRecovery>
        </maintenanceOptions>
        <metadataOptions>
            <httpEndpoint>enabled</httpEndpoint>
            <httpProtocolIpv6>disabled</httpProtocolIpv6>
            <httpPutResponseHopLimit>1</httpPutResponseHopLimit>
            <httpTokens>optional</httpTokens>
            <instanceMetadataTags>disabled</instanceMetadataTags>
        </metadataOptions>
        <monitoring>
            <enabled>{{ i.monitored }}</enabled>
        </monitoring>
        <networkInterfaceSet>
        {% for nic_index, nic in i.nics.items() %}
            <item>
                <associatePublicIpAddress>true</associatePublicIpAddress>
                <deleteOnTermination>{{ nic.delete_on_termination }}</deleteOnTermination>
                <description/>
                <deviceIndex>{{ nic.device_index }}</deviceIndex>
                <groupSet>
                    <groupId>{{ nic.group_set[0].group_id if nic.group_set }}</groupId>
                </groupSet>
                <interfaceType>{{ nic.interface_type }}</interfaceType>
                <ipv6AddressesSet/>
                <networkCardIndex>{{ nic_index }}</networkCardIndex>
                <privateIpAddressesSet>
                    {% for addr in nic.private_ip_addresses %}
                    <item>
                        <primary>{{ addr["Primary"] }}</primary>
                        <privateIpAddress>{{ addr["PrivateIpAddress"] }}</privateIpAddress>
                    </item>
                    {% endfor %}
                </privateIpAddressesSet>
                <subnetId>{{ nic.subnet.id }}</subnetId>
            </item>
        {% endfor %}
        </networkInterfaceSet>
        <placement>
            <availabilityZone>{{ i.placement }}</availabilityZone>
            <groupName/>
            <tenancy>default</tenancy>
        </placement>
        <privateDnsNameOptions>
            <enableResourceNameDnsAAAARecord>false</enableResourceNameDnsAAAARecord>
            <enableResourceNameDnsARecord>true</enableResourceNameDnsARecord>
            <hostnameType>ip-name</hostnameType>
        </privateDnsNameOptions>
        <tagSpecificationSet>
        {% for tag in i.tags %}
            <item>
                <resourceType>instance</resourceType>
                <tagSet>
                    <item>
                        <key>{{ tag.key }}</key>
                        <value>{{ tag.value }}</value>
                    </item>
                </tagSet>
            </item>
        {% endfor %}
        </tagSpecificationSet>
    </launchTemplateData>
</GetLaunchTemplateDataResponse>"""
