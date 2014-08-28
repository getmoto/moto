from __future__ import unicode_literals
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import instance_ids_from_querystring, image_ids_from_querystring, filters_from_querystring


class AmisResponse(BaseResponse):
    def create_image(self):
        name = self.querystring.get('Name')[0]
        if "Description" in self.querystring:
            description = self.querystring.get('Description')[0]
        else:
            description = ""
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        image = ec2_backend.create_image(instance_id, name, description)
        template = Template(CREATE_IMAGE_RESPONSE)
        return template.render(image=image)

    def deregister_image(self):
        ami_id = self.querystring.get('ImageId')[0]
        success = ec2_backend.deregister_image(ami_id)
        template = Template(DEREGISTER_IMAGE_RESPONSE)
        return template.render(success=str(success).lower())

    def describe_images(self):
        ami_ids = image_ids_from_querystring(self.querystring)
        filters = filters_from_querystring(self.querystring)
        images = ec2_backend.describe_images(ami_ids=ami_ids, filters=filters)
        template = Template(DESCRIBE_IMAGES_RESPONSE)
        return template.render(images=images)

    def describe_image_attribute(self):
        ami_id = self.querystring.get('ImageId')[0]
        groups = ec2_backend.get_launch_permission_groups(ami_id)
        template = Template(DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE)
        return template.render(ami_id=ami_id, groups=groups)

    def modify_image_attribute(self):
        ami_id = self.querystring.get('ImageId')[0]
        operation_type = self.querystring.get('OperationType')[0]
        group = self.querystring.get('UserGroup.1', [None])[0]
        user_id = self.querystring.get('UserId.1', [None])[0]
        if (operation_type == 'add'):
            ec2_backend.add_launch_permission(ami_id, user_id=user_id, group=group)
        elif (operation_type == 'remove'):
            ec2_backend.remove_launch_permission(ami_id, user_id=user_id, group=group)
        return MODIFY_IMAGE_ATTRIBUTE_RESPONSE

    def register_image(self):
        raise NotImplementedError('AMIs.register_image is not yet implemented')

    def reset_image_attribute(self):
        raise NotImplementedError('AMIs.reset_image_attribute is not yet implemented')


CREATE_IMAGE_RESPONSE = """<CreateImageResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</CreateImageResponse>"""

# TODO almost all of these params should actually be templated based on the ec2 image
DESCRIBE_IMAGES_RESPONSE = """<DescribeImagesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <imagesSet>
    {% for image in images %}
        <item>
          <imageId>{{ image.id }}</imageId>
          <imageLocation>amazon/getting-started</imageLocation>
          <imageState>{{ image.state }}</imageState>
          <imageOwnerId>111122223333</imageOwnerId>
          <isPublic>true</isPublic>
          <architecture>{{ image.architecture }}</architecture>
          <imageType>machine</imageType>
          <kernelId>{{ image.kernel_id }}</kernelId>
          <ramdiskId>ari-1a2b3c4d</ramdiskId>
          <imageOwnerAlias>amazon</imageOwnerAlias>
          <name>{{ image.name }}</name>
          {% if image.platform %}
             <platform>{{ image.platform }}</platform>
          {% endif %}
          <description>{{ image.description }}</description>
          <rootDeviceType>ebs</rootDeviceType>
          <rootDeviceName>/dev/sda</rootDeviceName>
          <blockDeviceMapping>
            <item>
              <deviceName>/dev/sda1</deviceName>
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

DESCRIBE_IMAGE_RESPONSE = """<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
   <{{ key }}>
     <value>{{ value }}</value>
   </{{key }}>
</DescribeImageAttributeResponse>"""

DEREGISTER_IMAGE_RESPONSE = """<DeregisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>{{ success }}</return>
</DeregisterImageResponse>"""

DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE = """
<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-08-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ ami_id }}</imageId>
   {% if not groups %}
      <launchPermission/>
   {% endif %}
   {% if groups %}
      <launchPermission>
         {% for group in groups %}
            <item>
               <group>{{ group }}</group>
            </item>
         {% endfor %}
      </launchPermission>
   {% endif %}
</DescribeImageAttributeResponse>"""

MODIFY_IMAGE_ATTRIBUTE_RESPONSE = """
<ModifyImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-08-15/">
   <return>true</return>
</ModifyImageAttributeResponse>
"""
