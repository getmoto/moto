from ._base_response import EC2BaseResponse
from ..exceptions import AuthFailureRestricted, InvalidRequest


class AmisResponse(EC2BaseResponse):
    def create_image(self) -> str:
        name = self.querystring.get("Name")[0]  # type: ignore[index]
        description = self._get_param("Description", if_none="")
        instance_id = self._get_param("InstanceId")
        tag_specifications = self._get_multi_param("TagSpecification")

        self.error_on_dryrun()

        image = self.ec2_backend.create_image(
            instance_id,
            name,
            description,
            tag_specifications=tag_specifications,
        )
        template = self.response_template(CREATE_IMAGE_RESPONSE)
        return template.render(image=image)

    def copy_image(self) -> str:
        source_image_id = self._get_param("SourceImageId")
        source_region = self._get_param("SourceRegion")
        name = self._get_param("Name")
        description = self._get_param("Description")

        self.error_on_dryrun()

        image = self.ec2_backend.copy_image(
            source_image_id, source_region, name, description
        )
        template = self.response_template(COPY_IMAGE_RESPONSE)
        return template.render(image=image)

    def deregister_image(self) -> str:
        ami_id = self._get_param("ImageId")

        self.error_on_dryrun()

        self.ec2_backend.deregister_image(ami_id)
        template = self.response_template(DEREGISTER_IMAGE_RESPONSE)
        return template.render(success="true")

    def describe_images(self) -> str:
        self.error_on_dryrun()
        ami_ids = self._get_multi_param("ImageId")
        filters = self._filters_from_querystring()
        owners = self._get_multi_param("Owner")
        exec_users = self._get_multi_param("ExecutableBy")
        images = self.ec2_backend.describe_images(
            ami_ids=ami_ids, filters=filters, exec_users=exec_users, owners=owners
        )
        template = self.response_template(DESCRIBE_IMAGES_RESPONSE)
        return template.render(images=images)

    def describe_image_attribute(self) -> str:
        ami_id = self._get_param("ImageId")
        attribute_name = self._get_param("Attribute")

        # only valid attributes as per
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_image_attribute.html
        valid_atrributes_list = {
            "description": "description",
            "kernel": "kernel_id",
            "ramdisk": "ramdisk",
            "launchPermission": {
                "groups": "launch_permission_groups",
                "users": "launch_permission_users",
            },
            "productCodes": "product_codes",
            "blockDeviceMapping": "bdm",
            "sriovNetSupport": "sriov",
            "bootMode": "boot_mode",
            "tpmSupport": "tmp",
            "uefiData": "uefi",
            "lastLaunchedTime": "lld",
            "imdsSupport": "imds",
        }
        if attribute_name not in valid_atrributes_list:
            raise InvalidRequest
        elif attribute_name == "blockDeviceMapping":
            # replicate real aws behaviour and throw and error
            # https://github.com/aws/aws-cli/issues/1083
            raise AuthFailureRestricted

        groups = None
        users = None
        attribute_value = None
        if attribute_name == "launchPermission":
            groups = self.ec2_backend.describe_image_attribute(
                ami_id, valid_atrributes_list[attribute_name]["groups"]  # type: ignore[index]
            )
            users = self.ec2_backend.describe_image_attribute(
                ami_id, valid_atrributes_list[attribute_name]["users"]  # type: ignore[index]
            )
        else:
            attribute_value = self.ec2_backend.describe_image_attribute(
                ami_id, valid_atrributes_list[attribute_name]
            )
        template = self.response_template(DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE)
        return template.render(
            ami_id=ami_id,
            users=users,
            groups=groups,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
        )

    def modify_image_attribute(self) -> str:
        ami_id = self._get_param("ImageId")
        operation_type = self._get_param("OperationType")
        group = self._get_param("UserGroup.1")
        user_ids = self._get_multi_param("UserId")

        self.error_on_dryrun()

        if operation_type == "add":
            self.ec2_backend.add_launch_permission(
                ami_id, user_ids=user_ids, group=group
            )
        elif operation_type == "remove":
            self.ec2_backend.remove_launch_permission(
                ami_id, user_ids=user_ids, group=group
            )
        return MODIFY_IMAGE_ATTRIBUTE_RESPONSE

    def register_image(self) -> str:
        name = self.querystring.get("Name")[0]  # type: ignore[index]
        description = self._get_param("Description", if_none="")

        self.error_on_dryrun()

        image = self.ec2_backend.register_image(name, description)
        template = self.response_template(REGISTER_IMAGE_RESPONSE)
        return template.render(image=image)

    def reset_image_attribute(self) -> str:
        self.error_on_dryrun()

        raise NotImplementedError("AMIs.reset_image_attribute is not yet implemented")


CREATE_IMAGE_RESPONSE = """<CreateImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</CreateImageResponse>"""

COPY_IMAGE_RESPONSE = """<CopyImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>60bc441d-fa2c-494d-b155-5d6a3EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</CopyImageResponse>"""

# TODO almost all of these params should actually be templated based on
# the ec2 image
DESCRIBE_IMAGES_RESPONSE = """<DescribeImagesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <imagesSet>
    {% for image in images %}
        <item>
          <imageId>{{ image.id }}</imageId>
          <imageLocation>{{ image.image_location }}</imageLocation>
          <imageState>{{ image.state }}</imageState>
          <imageOwnerId>{{ image.owner_id }}</imageOwnerId>
          <isPublic>{{ image.is_public_string }}</isPublic>
          <architecture>{{ image.architecture }}</architecture>
          <imageType>{{ image.image_type }}</imageType>
          <kernelId>{{ image.kernel_id }}</kernelId>
          <ramdiskId>ari-1a2b3c4d</ramdiskId>
          <imageOwnerAlias>amazon</imageOwnerAlias>
          <creationDate>{{ image.creation_date }}</creationDate>
          <name>{{ image.name }}</name>
          {% if image.platform %}
             <platform>{{ image.platform }}</platform>
          {% endif %}
          <description>{{ image.description }}</description>
          <rootDeviceType>{{ image.root_device_type }}</rootDeviceType>
          <rootDeviceName>{{ image.root_device_name }}</rootDeviceName>
          <blockDeviceMapping>
            <item>
              <deviceName>{{ image.root_device_name }}</deviceName>
              <ebs>
                <snapshotId>{{ image.ebs_snapshot.id }}</snapshotId>
                <volumeSize>15</volumeSize>
                <deleteOnTermination>false</deleteOnTermination>
                <volumeType>standard</volumeType>
              </ebs>
            </item>
          </blockDeviceMapping>
          <virtualizationType>{{ image.virtualization_type }}</virtualizationType>
          <tagSet>
            {% for tag in image.get_tags() %}
              <item>
                <resourceId>{{ tag.resource_id }}</resourceId>
                <resourceType>{{ tag.resource_type }}</resourceType>
                <key>{{ tag.key }}</key>
                <value>{{ tag.value }}</value>
              </item>
            {% endfor %}
          </tagSet>
          <hypervisor>xen</hypervisor>
        </item>
    {% endfor %}
  </imagesSet>
</DescribeImagesResponse>"""

DESCRIBE_IMAGE_RESPONSE = """<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
   <{{ key }}>
     <value>{{ value }}</value>
   </{{key }}>
</DescribeImageAttributeResponse>"""

DEREGISTER_IMAGE_RESPONSE = """<DeregisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>{{ success }}</return>
</DeregisterImageResponse>"""

DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE = """
<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ ami_id }}</imageId>
    <{{ attribute_name }}>
    {% if attribute_name == 'productCodes' %}
        {% for value in attribute_value %}
        <item>
            <productCode>{{ value }}</productCode>
            <type>marketplace</type>
        </item>
        {% endfor %}
    {% endif %}
    {% if attribute_name == 'launchPermission' %}
         {% if groups %}
            {% for group in groups %}
               <item>
                  <group>{{ group }}</group>
               </item>
            {% endfor %}
         {% endif %}
         {% if users %}
            {% for user in users %}
               <item>
                  <userId>{{ user }}</userId>
               </item>
            {% endfor %}
         {% endif %}
    {% endif %}
    {% if attribute_name not in ['launchPermission', 'productCodes'] %}
            <value>{{ attribute_value }}</value>
    {% endif %}
    </{{ attribute_name }}>
</DescribeImageAttributeResponse>"""

MODIFY_IMAGE_ATTRIBUTE_RESPONSE = """
<ModifyImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <return>true</return>
</ModifyImageAttributeResponse>
"""

REGISTER_IMAGE_RESPONSE = """<RegisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</RegisterImageResponse>"""
