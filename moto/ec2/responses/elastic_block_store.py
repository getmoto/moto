from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class ElasticBlockStore(BaseResponse):

    def attach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]
        if self.is_not_dryrun('AttachVolume'):
            attachment = self.ec2_backend.attach_volume(
                volume_id, instance_id, device_path)
            template = self.response_template(ATTACHED_VOLUME_RESPONSE)
            return template.render(attachment=attachment)

    def copy_snapshot(self):
        if self.is_not_dryrun('CopySnapshot'):
            raise NotImplementedError(
                'ElasticBlockStore.copy_snapshot is not yet implemented')

    def create_snapshot(self):
        description = self.querystring.get('Description', [None])[0]
        volume_id = self.querystring.get('VolumeId')[0]
        if self.is_not_dryrun('CreateSnapshot'):
            snapshot = self.ec2_backend.create_snapshot(volume_id, description)
            template = self.response_template(CREATE_SNAPSHOT_RESPONSE)
            return template.render(snapshot=snapshot)

    def create_volume(self):
        size = self.querystring.get('Size', [None])[0]
        zone = self.querystring.get('AvailabilityZone', [None])[0]
        snapshot_id = self.querystring.get('SnapshotId', [None])[0]
        encrypted = self.querystring.get('Encrypted', ['false'])[0]
        if self.is_not_dryrun('CreateVolume'):
            volume = self.ec2_backend.create_volume(
                size, zone, snapshot_id, encrypted)
            template = self.response_template(CREATE_VOLUME_RESPONSE)
            return template.render(volume=volume)

    def delete_snapshot(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        if self.is_not_dryrun('DeleteSnapshot'):
            self.ec2_backend.delete_snapshot(snapshot_id)
            return DELETE_SNAPSHOT_RESPONSE

    def delete_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        if self.is_not_dryrun('DeleteVolume'):
            self.ec2_backend.delete_volume(volume_id)
            return DELETE_VOLUME_RESPONSE

    def describe_snapshots(self):
        filters = filters_from_querystring(self.querystring)
        # querystring for multiple snapshotids results in SnapshotId.1,
        # SnapshotId.2 etc
        snapshot_ids = ','.join(
            [','.join(s[1]) for s in self.querystring.items() if 'SnapshotId' in s[0]])
        snapshots = self.ec2_backend.describe_snapshots(filters=filters)
        # Describe snapshots to handle filter on snapshot_ids
        snapshots = [
            s for s in snapshots if s.id in snapshot_ids] if snapshot_ids else snapshots
        template = self.response_template(DESCRIBE_SNAPSHOTS_RESPONSE)
        return template.render(snapshots=snapshots)

    def describe_volumes(self):
        filters = filters_from_querystring(self.querystring)
        # querystring for multiple volumeids results in VolumeId.1, VolumeId.2
        # etc
        volume_ids = ','.join(
            [','.join(v[1]) for v in self.querystring.items() if 'VolumeId' in v[0]])
        volumes = self.ec2_backend.describe_volumes(filters=filters)
        # Describe volumes to handle filter on volume_ids
        volumes = [
            v for v in volumes if v.id in volume_ids] if volume_ids else volumes
        template = self.response_template(DESCRIBE_VOLUMES_RESPONSE)
        return template.render(volumes=volumes)

    def describe_volume_attribute(self):
        raise NotImplementedError(
            'ElasticBlockStore.describe_volume_attribute is not yet implemented')

    def describe_volume_status(self):
        raise NotImplementedError(
            'ElasticBlockStore.describe_volume_status is not yet implemented')

    def detach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]
        if self.is_not_dryrun('DetachVolume'):
            attachment = self.ec2_backend.detach_volume(
                volume_id, instance_id, device_path)
            template = self.response_template(DETATCH_VOLUME_RESPONSE)
            return template.render(attachment=attachment)

    def enable_volume_io(self):
        if self.is_not_dryrun('EnableVolumeIO'):
            raise NotImplementedError(
                'ElasticBlockStore.enable_volume_io is not yet implemented')

    def import_volume(self):
        if self.is_not_dryrun('ImportVolume'):
            raise NotImplementedError(
                'ElasticBlockStore.import_volume is not yet implemented')

    def describe_snapshot_attribute(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        groups = self.ec2_backend.get_create_volume_permission_groups(
            snapshot_id)
        template = self.response_template(
            DESCRIBE_SNAPSHOT_ATTRIBUTES_RESPONSE)
        return template.render(snapshot_id=snapshot_id, groups=groups)

    def modify_snapshot_attribute(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        operation_type = self.querystring.get('OperationType')[0]
        group = self.querystring.get('UserGroup.1', [None])[0]
        user_id = self.querystring.get('UserId.1', [None])[0]
        if self.is_not_dryrun('ModifySnapshotAttribute'):
            if (operation_type == 'add'):
                self.ec2_backend.add_create_volume_permission(
                    snapshot_id, user_id=user_id, group=group)
            elif (operation_type == 'remove'):
                self.ec2_backend.remove_create_volume_permission(
                    snapshot_id, user_id=user_id, group=group)
            return MODIFY_SNAPSHOT_ATTRIBUTE_RESPONSE

    def modify_volume_attribute(self):
        if self.is_not_dryrun('ModifyVolumeAttribute'):
            raise NotImplementedError(
                'ElasticBlockStore.modify_volume_attribute is not yet implemented')

    def reset_snapshot_attribute(self):
        if self.is_not_dryrun('ResetSnapshotAttribute'):
            raise NotImplementedError(
                'ElasticBlockStore.reset_snapshot_attribute is not yet implemented')


CREATE_VOLUME_RESPONSE = """<CreateVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <volumeId>{{ volume.id }}</volumeId>
  <size>{{ volume.size }}</size>
  {% if volume.snapshot_id %}
    <snapshotId>{{ volume.snapshot_id }}</snapshotId>
  {% else %}
    <snapshotId/>
  {% endif %}
  <encrypted>{{ volume.encrypted }}</encrypted>
  <availabilityZone>{{ volume.zone.name }}</availabilityZone>
  <status>creating</status>
  <createTime>{{ volume.create_time}}</createTime>
  <volumeType>standard</volumeType>
</CreateVolumeResponse>"""

DESCRIBE_VOLUMES_RESPONSE = """<DescribeVolumesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <volumeSet>
      {% for volume in volumes %}
          <item>
             <volumeId>{{ volume.id }}</volumeId>
             <size>{{ volume.size }}</size>
             {% if volume.snapshot_id %}
               <snapshotId>{{ volume.snapshot_id }}</snapshotId>
             {% else %}
               <snapshotId/>
             {% endif %}
             <encrypted>{{ volume.encrypted }}</encrypted>
             <availabilityZone>{{ volume.zone.name }}</availabilityZone>
             <status>{{ volume.status }}</status>
             <createTime>{{ volume.create_time}}</createTime>
             <attachmentSet>
                {% if volume.attachment %}
                    <item>
                       <volumeId>{{ volume.id }}</volumeId>
                       <instanceId>{{ volume.attachment.instance.id }}</instanceId>
                       <device>{{ volume.attachment.device }}</device>
                       <status>attached</status>
                       <attachTime>{{volume.attachment.attach_time}}</attachTime>
                       <deleteOnTermination>false</deleteOnTermination>
                    </item>
                {% endif %}
             </attachmentSet>
             <tagSet>
               {% for tag in volume.get_tags() %}
                 <item>
                   <resourceId>{{ tag.resource_id }}</resourceId>
                   <resourceType>{{ tag.resource_type }}</resourceType>
                   <key>{{ tag.key }}</key>
                   <value>{{ tag.value }}</value>
                 </item>
               {% endfor %}
             </tagSet>
             <volumeType>standard</volumeType>
          </item>
      {% endfor %}
   </volumeSet>
</DescribeVolumesResponse>"""

DELETE_VOLUME_RESPONSE = """<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteVolumeResponse>"""

ATTACHED_VOLUME_RESPONSE = """<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <volumeId>{{ attachment.volume.id }}</volumeId>
  <instanceId>{{ attachment.instance.id }}</instanceId>
  <device>{{ attachment.device }}</device>
  <status>attaching</status>
  <attachTime>{{attachment.attach_time}}</attachTime>
</AttachVolumeResponse>"""

DETATCH_VOLUME_RESPONSE = """<DetachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <volumeId>{{ attachment.volume.id }}</volumeId>
   <instanceId>{{ attachment.instance.id }}</instanceId>
   <device>{{ attachment.device }}</device>
   <status>detaching</status>
   <attachTime>2013-10-04T17:38:53.000Z</attachTime>
</DetachVolumeResponse>"""

CREATE_SNAPSHOT_RESPONSE = """<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <snapshotId>{{ snapshot.id }}</snapshotId>
  <volumeId>{{ snapshot.volume.id }}</volumeId>
  <status>pending</status>
  <startTime>{{ snapshot.start_time}}</startTime>
  <progress>60%</progress>
  <ownerId>123456789012</ownerId>
  <volumeSize>{{ snapshot.volume.size }}</volumeSize>
  <description>{{ snapshot.description }}</description>
  <encrypted>{{ snapshot.encrypted }}</encrypted>
</CreateSnapshotResponse>"""

DESCRIBE_SNAPSHOTS_RESPONSE = """<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <snapshotSet>
      {% for snapshot in snapshots %}
          <item>
             <snapshotId>{{ snapshot.id }}</snapshotId>
            <volumeId>{{ snapshot.volume.id }}</volumeId>
             <status>{{ snapshot.status }}</status>
             <startTime>{{ snapshot.start_time}}</startTime>
             <progress>100%</progress>
             <ownerId>123456789012</ownerId>
            <volumeSize>{{ snapshot.volume.size }}</volumeSize>
             <description>{{ snapshot.description }}</description>
             <encrypted>{{ snapshot.encrypted }}</encrypted>
             <tagSet>
               {% for tag in snapshot.get_tags() %}
                 <item>
                   <resourceId>{{ tag.resource_id }}</resourceId>
                   <resourceType>{{ tag.resource_type }}</resourceType>
                   <key>{{ tag.key }}</key>
                   <value>{{ tag.value }}</value>
                 </item>
               {% endfor %}
             </tagSet>
          </item>
      {% endfor %}
   </snapshotSet>
</DescribeSnapshotsResponse>"""

DELETE_SNAPSHOT_RESPONSE = """<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSnapshotResponse>"""

DESCRIBE_SNAPSHOT_ATTRIBUTES_RESPONSE = """
<DescribeSnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
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
<ModifySnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>666d2944-9276-4d6a-be12-1f4ada972fd8</requestId>
    <return>true</return>
</ModifySnapshotAttributeResponse>
"""
