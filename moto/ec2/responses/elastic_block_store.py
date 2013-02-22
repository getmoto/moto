from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ElasticBlockStore(object):
    def attach_volume(self):
        raise NotImplementedError('ElasticBlockStore.attach_volume is not yet implemented')

    def copy_snapshot(self):
        raise NotImplementedError('ElasticBlockStore.copy_snapshot is not yet implemented')

    def create_snapshot(self):
        raise NotImplementedError('ElasticBlockStore.create_snapshot is not yet implemented')

    def create_volume(self):
        raise NotImplementedError('ElasticBlockStore.create_volume is not yet implemented')

    def delete_snapshot(self):
        raise NotImplementedError('ElasticBlockStore.delete_snapshot is not yet implemented')

    def delete_volume(self):
        raise NotImplementedError('ElasticBlockStore.delete_volume is not yet implemented')

    def describe_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.describe_snapshot_attribute is not yet implemented')

    def describe_snapshots(self):
        raise NotImplementedError('ElasticBlockStore.describe_snapshots is not yet implemented')

    def describe_volumes(self):
        raise NotImplementedError('ElasticBlockStore.describe_volumes is not yet implemented')

    def describe_volume_attribute(self):
        raise NotImplementedError('ElasticBlockStore.describe_volume_attribute is not yet implemented')

    def describe_volume_status(self):
        raise NotImplementedError('ElasticBlockStore.describe_volume_status is not yet implemented')

    def detach_volume(self):
        raise NotImplementedError('ElasticBlockStore.detach_volume is not yet implemented')

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

