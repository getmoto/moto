from __future__ import unicode_literals

import copy
import datetime
import string
import os

from moto.compat import OrderedDict
from moto.core.utils import iso_8601_datetime_with_milliseconds
from .base import BaseRDSBackend, BaseRDSModel
from .event import EventMixin
from .tag import TaggableRDSResource
from ..exceptions import (
    DBSnapshotAlreadyExists,
    DBSnapshotNotFound,
    InvalidDBSnapshotIdentifierValue,
    SnapshotQuotaExceeded)


class DBSnapshot(TaggableRDSResource, EventMixin, BaseRDSModel):

    resource_type = 'snapshot'
    event_source_type = 'db-snapshot'

    @staticmethod
    def _is_identifier_valid(db_snapshot_identifier):
        """
        :param db_snapshot_identifier:

        Constraints:

        Cannot be null, empty, or blank
        Must contain from 1 to 255 letters, numbers, or hyphens
        First character must be a letter
        Cannot end with a hyphen or contain two consecutive hyphens
        Example: my-snapshot-id

        :return:
        """
        is_valid = True
        if db_snapshot_identifier is None or db_snapshot_identifier == '':
            is_valid = False
        if len(db_snapshot_identifier) < 1 or len(db_snapshot_identifier) > 255:
            is_valid = False
        if not db_snapshot_identifier[0].isalpha():
            is_valid = False
        if db_snapshot_identifier[-1] == '-':
            is_valid = False
        if db_snapshot_identifier.find('--') != -1:
            is_valid = False
        valid_chars = ''.join([string.digits, string.ascii_letters, '-'])
        if not all(char in valid_chars for char in db_snapshot_identifier):
            is_valid = False
        return is_valid

    def __init__(self, backend, identifier, db_instance, snapshot_type='manual', tags=None, kms_key_id=None):
        super(DBSnapshot, self).__init__(backend)
        if snapshot_type == 'manual':
            if not self._is_identifier_valid(identifier):
                raise InvalidDBSnapshotIdentifierValue(identifier)
        self.db_snapshot_identifier = identifier
        self.snapshot_type = snapshot_type
        self.status = 'available'
        self.created_at = iso_8601_datetime_with_milliseconds(datetime.datetime.now())
        # If tags are provided at creation, AWS does *not* copy tags from the
        # db_instance (even if copy_tags_to_snapshot is True).
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Tagging.html
        if tags:
            self.add_tags(tags)
        elif db_instance.copy_tags_to_snapshot:
            self.add_tags(db_instance.tags)

        self.db_instance = copy.copy(db_instance)
        self.db_instance_identifier = self.db_instance.resource_id
        self.engine = self.db_instance.engine
        self.allocated_storage = self.db_instance.allocated_storage
        if kms_key_id is not None:
            self.kms_key_id = self.db_instance.kms_key_id = kms_key_id
            self.encrypted = self.db_instance.storage_encrypted = True
        else:
            self.kms_key_id = self.db_instance.kms_key_id
            self.encrypted = self.db_instance.storage_encrypted
        self.port = self.db_instance.port
        self.availability_zone = self.db_instance.availability_zone
        self.engine_version = self.db_instance.engine_version
        self.master_username = self.db_instance.master_username
        self.storage_type = self.db_instance.storage_type
        self.iops = self.db_instance.iops

    @property
    def resource_id(self):
        return self.db_snapshot_identifier

    @property
    def db_snapshot_arn(self):
        return self.arn

    @property
    def snapshot_create_time(self):
        return self.created_at


class DBSnapshotBackend(BaseRDSBackend):

    def __init__(self):
        super(DBSnapshotBackend, self).__init__()
        self.db_snapshots = OrderedDict()

    def get_db_snapshot(self, db_snapshot_identifier):
        if db_snapshot_identifier not in self.db_snapshots:
            raise DBSnapshotNotFound(db_snapshot_identifier)
        return self.db_snapshots[db_snapshot_identifier]

    def copy_db_snapshot(self, source_db_snapshot_identifier, target_db_snapshot_identifier,
                         kms_key_id=None, tags=None):
        if target_db_snapshot_identifier in self.db_snapshots:
            raise DBSnapshotAlreadyExists(target_db_snapshot_identifier)
        if len(self.db_snapshots) >= int(os.environ.get('MOTO_RDS_SNAPSHOT_LIMIT', '100')):
            raise SnapshotQuotaExceeded()
        if kms_key_id is not None:
            key = self.kms.describe_key(str(kms_key_id))
            # We do this in case an alias was passed in.
            kms_key_id = key.id
        source_snapshot = self.get_db_snapshot(source_db_snapshot_identifier)
        target_snapshot = DBSnapshot(self,
                                     target_db_snapshot_identifier,
                                     source_snapshot.db_instance,
                                     tags=tags,
                                     kms_key_id=kms_key_id)
        self.db_snapshots[target_db_snapshot_identifier] = target_snapshot
        return target_snapshot

    def create_db_snapshot(self, db_instance_identifier, db_snapshot_identifier, tags=None, snapshot_type='manual'):
        if db_snapshot_identifier in self.db_snapshots:
            raise DBSnapshotAlreadyExists(db_snapshot_identifier)
        if len(self.db_snapshots) >= int(os.environ.get('MOTO_RDS_SNAPSHOT_LIMIT', '100')):
            raise SnapshotQuotaExceeded()
        db_instance = self.get_db_instance(db_instance_identifier)
        snapshot = DBSnapshot(self, db_snapshot_identifier, db_instance, snapshot_type, tags)
        snapshot.add_event('DB_SNAPSHOT_CREATE_{}_START'.format(snapshot_type.upper()))
        snapshot.add_event('DB_SNAPSHOT_CREATE_{}_FINISH'.format(snapshot_type.upper()))
        self.db_snapshots[db_snapshot_identifier] = snapshot
        return snapshot

    def delete_db_snapshot(self, db_snapshot_identifier):
        snapshot = self.get_db_snapshot(db_snapshot_identifier)
        snapshot.delete_events()
        return self.db_snapshots.pop(db_snapshot_identifier)

    def describe_db_snapshots(self, db_instance_identifier=None, db_snapshot_identifier=None, snapshot_type=None, **kwargs):
        if db_snapshot_identifier:
            return [self.get_db_snapshot(db_snapshot_identifier)]
        snapshot_types = ['automated', 'manual'] if snapshot_type is None else [snapshot_type]
        if db_instance_identifier:
            db_instance_snapshots = []
            for snapshot in self.db_snapshots.values():
                if snapshot.db_instance_identifier == db_instance_identifier:
                    if snapshot.snapshot_type in snapshot_types:
                        db_instance_snapshots.append(snapshot)
            return db_instance_snapshots
        return self.db_snapshots.values()
