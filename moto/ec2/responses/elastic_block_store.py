from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ElasticBlockStore(object):
    def attach_volume(self):
        return NotImplemented

    def copy_snapshot(self):
        return NotImplemented

    def create_snapshot(self):
        return NotImplemented

    def create_volume(self):
        return NotImplemented

    def delete_snapshot(self):
        return NotImplemented

    def delete_volume(self):
        return NotImplemented

    def describe_snapshot_attribute(self):
        return NotImplemented

    def describe_snapshots(self):
        return NotImplemented

    def describe_volumes(self):
        return NotImplemented

    def describe_volume_attribute(self):
        return NotImplemented

    def describe_volume_status(self):
        return NotImplemented

    def detach_volume(self):
        return NotImplemented

    def enable_volume_io(self):
        return NotImplemented

    def import_volume(self):
        return NotImplemented

    def modify_snapshot_attribute(self):
        return NotImplemented

    def modify_volume_attribute(self):
        return NotImplemented

    def reset_snapshot_attribute(self):
        return NotImplemented

