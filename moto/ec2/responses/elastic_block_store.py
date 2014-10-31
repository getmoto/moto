from __future__ import unicode_literals
from jinja2 import Template

from moto.core.responses import BaseResponse


class ElasticBlockStore(BaseResponse):
    def attach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]

        attachment = self.ec2_backend.attach_volume(volume_id, instance_id, device_path)
        template = Template(ATTACHED_VOLUME_RESPONSE)
        return template.render(attachment=attachment)

    def copy_snapshot(self):
        raise NotImplementedError('ElasticBlockStore.copy_snapshot is not yet implemented')

    def create_snapshot(self):
        description = None
        if 'Description' in self.querystring:
            description = self.querystring.get('Description')[0]
        volume_id = self.querystring.get('VolumeId')[0]
        snapshot = self.ec2_backend.create_snapshot(volume_id, description)
        template = Template(CREATE_SNAPSHOT_RESPONSE)
        return template.render(snapshot=snapshot)

    def create_volume(self):
        size = self.querystring.get('Size')[0]
        zone = self.querystring.get('AvailabilityZone')[0]
        volume = self.ec2_backend.create_volume(size, zone)
        template = Template(CREATE_VOLUME_RESPONSE)
        return template.render(volume=volume)

    def delete_snapshot(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        success = self.ec2_backend.delete_snapshot(snapshot_id)
        return DELETE_SNAPSHOT_RESPONSE

    def delete_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        success = self.ec2_backend.delete_volume(volume_id)
        return DELETE_VOLUME_RESPONSE

    def describe_snapshots(self):
        snapshots = self.ec2_backend.describe_snapshots()
        template = Template(DESCRIBE_SNAPSHOTS_RESPONSE)
        return template.render(snapshots=snapshots)

    def describe_volumes(self):
        volumes = self.ec2_backend.describe_volumes()
        template = Template(DESCRIBE_VOLUMES_RESPONSE)
        return template.render(volumes=volumes)

    def describe_volume_attribute(self):
        raise NotImplementedError('ElasticBlockStore.describe_volume_attribute is not yet implemented')

    def describe_volume_status(self):
        raise NotImplementedError('ElasticBlockStore.describe_volume_status is not yet implemented')

    def detach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]

        attachment = self.ec2_backend.detach_volume(volume_id, instance_id, device_path)
        template = Template(DETATCH_VOLUME_RESPONSE)
        return template.render(attachment=attachment)

    def enable_volume_io(self):
        raise NotImplementedError('ElasticBlockStore.enable_volume_io is not yet implemented')

    def import_volume(self):
        raise NotImplementedError('ElasticBlockStore.import_volume is not yet implemented')

    def describe_snapshot_attribute(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        groups = self.ec2_backend.get_create_volume_permission_groups(snapshot_id)
        template = Template(DESCRIBE_SNAPSHOT_ATTRIBUTES_RESPONSE)
        return template.render(snapshot_id=snapshot_id, groups=groups)

    def modify_snapshot_attribute(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        operation_type = self.querystring.get('OperationType')[0]
        group = self.querystring.get('UserGroup.1', [None])[0]
        user_id = self.querystring.get('UserId.1', [None])[0]
        if (operation_type == 'add'):
            self.ec2_backend.add_create_volume_permission(snapshot_id, user_id=user_id, group=group)
        elif (operation_type == 'remove'):
            self.ec2_backend.remove_create_volume_permission(snapshot_id, user_id=user_id, group=group)
        return MODIFY_SNAPSHOT_ATTRIBUTE_RESPONSE

    def modify_volume_attribute(self):
        raise NotImplementedError('ElasticBlockStore.modify_volume_attribute is not yet implemented')

    def reset_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.reset_snapshot_attribute is not yet implemented')


CREATE_VOLUME_RESPONSE = """<CreateVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <volumeId>{{ volume.id }}</volumeId>
  <size>{{ volume.size }}</size>
  <snapshotId/>
  <availabilityZone>{{ volume.zone.name }}</availabilityZone>
  <status>creating</status>
  <createTime>YYYY-MM-DDTHH:MM:SS.000Z</createTime>
  <volumeType>standard</volumeType>
</CreateVolumeResponse>"""

DESCRIBE_VOLUMES_RESPONSE = """<DescribeVolumesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <volumeSet>
      {% for volume in volumes %}
          <item>
             <volumeId>{{ volume.id }}</volumeId>
             <size>{{ volume.size }}</size>
             <snapshotId/>
             <availabilityZone>{{ volume.zone.name }}</availabilityZone>
             <status>{{ volume.status }}</status>
             <createTime>YYYY-MM-DDTHH:MM:SS.SSSZ</createTime>
             <attachmentSet>
                {% if volume.attachment %}
                    <item>
                       <volumeId>{{ volume.id }}</volumeId>
                       <instanceId>{{ volume.attachment.instance.id }}</instanceId>
                       <device>{{ volume.attachment.device }}</device>
                       <status>attached</status>
                       <attachTime>YYYY-MM-DDTHH:MM:SS.SSSZ</attachTime>
                       <deleteOnTermination>false</deleteOnTermination>
                    </item>
                {% endif %}
             </attachmentSet>
             <volumeType>standard</volumeType>
          </item>
      {% endfor %}
   </volumeSet>
</DescribeVolumesResponse>"""

DELETE_VOLUME_RESPONSE = """<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteVolumeResponse>"""

ATTACHED_VOLUME_RESPONSE = """<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <volumeId>{{ attachment.volume.id }}</volumeId>
  <instanceId>{{ attachment.instance.id }}</instanceId>
  <device>{{ attachment.device }}</device>
  <status>attaching</status>
  <attachTime>YYYY-MM-DDTHH:MM:SS.000Z</attachTime>
</AttachVolumeResponse>"""

DETATCH_VOLUME_RESPONSE = """<DetachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <volumeId>{{ attachment.volume.id }}</volumeId>
   <instanceId>{{ attachment.instance.id }}</instanceId>
   <device>{{ attachment.device }}</device>
   <status>detaching</status>
   <attachTime>YYYY-MM-DDTHH:MM:SS.000Z</attachTime>
</DetachVolumeResponse>"""

CREATE_SNAPSHOT_RESPONSE = """<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <snapshotId>{{ snapshot.id }}</snapshotId>
  <volumeId>{{ snapshot.volume.id }}</volumeId>
  <status>pending</status>
  <startTime>YYYY-MM-DDTHH:MM:SS.000Z</startTime>
  <progress>60%</progress>
  <ownerId>111122223333</ownerId>
  <volumeSize>{{ snapshot.volume.size }}</volumeSize>
  <description>{{ snapshot.description }}</description>
</CreateSnapshotResponse>"""

DESCRIBE_SNAPSHOTS_RESPONSE = """<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <snapshotSet>
      {% for snapshot in snapshots %}
          <item>
             <snapshotId>{{ snapshot.id }}</snapshotId>
             <volumeId>{{ snapshot.volume.id }}</volumeId>
             <status>pending</status>
             <startTime>YYYY-MM-DDTHH:MM:SS.SSSZ</startTime>
             <progress>30%</progress>
             <ownerId>111122223333</ownerId>
             <volumeSize>{{ snapshot.volume.size }}</volumeSize>
             <description>{{ snapshot.description }}</description>
             <tagSet>
             </tagSet>
          </item>
      {% endfor %}
   </snapshotSet>
</DescribeSnapshotsResponse>"""

DELETE_SNAPSHOT_RESPONSE = """<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSnapshotResponse>"""

DESCRIBE_SNAPSHOT_ATTRIBUTES_RESPONSE = """
<DescribeSnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
    <requestId>a9540c9f-161a-45d8-9cc1-1182b89ad69f</requestId>
    <snapshotId>snap-a0332ee0</snapshotId>
   {% if not groups %}
      <createVolumePermission/>
   {% endif %}
   {% if groups %}
      <createVolumePermission>
         {% for group in groups %}
            <item>
               <group>{{ group }}</group>
            </item>
         {% endfor %}
      </createVolumePermission>
   {% endif %}
</DescribeSnapshotAttributeResponse>
"""

MODIFY_SNAPSHOT_ATTRIBUTE_RESPONSE = """
<ModifySnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
    <requestId>666d2944-9276-4d6a-be12-1f4ada972fd8</requestId>
    <return>true</return>
</ModifySnapshotAttributeResponse>
"""
