from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import instance_ids_from_querystring, image_ids_from_querystring


class AmisResponse(object):
    def create_image(self):
        name = self.querystring.get('Name')[0]
        if "Description" in self.querystring:
            description = self.querystring.get('Description')[0]
        else:
            description = ""
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        image = ec2_backend.create_image(instance_id, name, description)
        if not image:
            return "There is not instance with id {0}".format(instance_id), dict(status=404)
        template = Template(CREATE_IMAGE_RESPONSE)
        return template.render(image=image)

    def deregister_image(self):
        ami_id = self.querystring.get('ImageId')[0]
        success = ec2_backend.deregister_image(ami_id)
        template = Template(DEREGISTER_IMAGE_RESPONSE)
        rendered = template.render(success=str(success).lower())
        if success:
            return rendered
        else:
            return rendered, dict(status=404)

    def describe_image_attribute(self):
        raise NotImplementedError('AMIs.describe_image_attribute is not yet implemented')

    def describe_images(self):
        ami_ids = image_ids_from_querystring(self.querystring)
        images = ec2_backend.describe_images(ami_ids=ami_ids)
        template = Template(DESCRIBE_IMAGES_RESPONSE)
        return template.render(images=images)

    def modify_image_attribute(self):
        raise NotImplementedError('AMIs.modify_image_attribute is not yet implemented')

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
          <imageState>available</imageState>
          <imageOwnerId>111122223333</imageOwnerId>
          <isPublic>true</isPublic>
          <architecture>i386</architecture>
          <imageType>machine</imageType>
          <kernelId>{{ image.kernel_id }}</kernelId>
          <ramdiskId>ari-1a2b3c4d</ramdiskId>
          <imageOwnerAlias>amazon</imageOwnerAlias>
          <name>{{ image.name }}</name>
          <description>{{ image.description }}</description>
          <rootDeviceType>ebs</rootDeviceType>
          <rootDeviceName>/dev/sda</rootDeviceName>
          <blockDeviceMapping>
            <item>
              <deviceName>/dev/sda1</deviceName>
              <ebs>
                <snapshotId>snap-1a2b3c4d</snapshotId>
                <volumeSize>15</volumeSize>
                <deleteOnTermination>false</deleteOnTermination>
                <volumeType>standard</volumeType>
              </ebs>
            </item>
          </blockDeviceMapping>
          <virtualizationType>{{ image.virtualization_type }}</virtualizationType>
          <tagSet/>
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
