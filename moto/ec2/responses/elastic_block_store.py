from jinja2 import Template

from moto.ec2.models import ec2_backend


class ElasticBlockStore(object):
    def attach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]

        attachment = ec2_backend.attach_volume(volume_id, instance_id, device_path)
        if not attachment:
            return "", dict(status=404)
        template = Template(ATTACHED_VOLUME_RESPONSE)
        return template.render(attachment=attachment)

    def copy_snapshot(self):
        raise NotImplementedError('ElasticBlockStore.copy_snapshot is not yet implemented')

    def create_snapshot(self):
        description = None
        if 'Description' in self.querystring:
            description = self.querystring.get('Description')[0]
        volume_id = self.querystring.get('VolumeId')[0]
        snapshot = ec2_backend.create_snapshot(volume_id, description)
        template = Template(CREATE_SNAPSHOT_RESPONSE)
        return template.render(snapshot=snapshot)

    def create_volume(self):
        size = self.querystring.get('Size')[0]
        zone = self.querystring.get('AvailabilityZone')[0]
        volume = ec2_backend.create_volume(size, zone)
        template = Template(CREATE_VOLUME_RESPONSE)
        return template.render(volume=volume)

    def delete_snapshot(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        success = ec2_backend.delete_snapshot(snapshot_id)
        if not success:
            # Snapshot doesn't exist
            return "Snapshot with id {0} does not exist".format(snapshot_id), dict(status=404)
        return DELETE_SNAPSHOT_RESPONSE

    def delete_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        success = ec2_backend.delete_volume(volume_id)
        if not success:
            # Volume doesn't exist
            return "Volume with id {0} does not exist".format(volume_id), dict(status=404)
        return DELETE_VOLUME_RESPONSE

    def describe_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.describe_snapshot_attribute is not yet implemented')

    def describe_snapshots(self):
        snapshots = ec2_backend.describe_snapshots()
        template = Template(DESCRIBE_SNAPSHOTS_RESPONSE)
        return template.render(snapshots=snapshots)

    def describe_volumes(self):
        volumes = ec2_backend.describe_volumes()
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

        attachment = ec2_backend.detach_volume(volume_id, instance_id, device_path)
        if not attachment:
            # Volume wasn't attached
            return "Volume {0} can not be detached from {1} because it is not attached".format(volume_id, instance_id), dict(status=404)
        template = Template(DETATCH_VOLUME_RESPONSE)
        return template.render(attachment=attachment)

    def enable_volume_io(self):
        raise NotImplementedError('ElasticBlockStore.enable_volume_io is not yet implemented')

    def import_volume(self):
        raise NotImplementedError('ElasticBlockStore.import_volume is not yet implemented')

    def modify_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.modify_snapshot_attribute is not yet implemented')

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
