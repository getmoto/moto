from __future__ import unicode_literals

import copy

from moto.compat import OrderedDict
from .base import BaseRDSBackend, BaseRDSModel
from .tag import TaggableRDSResource
from ..exceptions import (
    DBClusterSnapshotAlreadyExists,
    DBClusterSnapshotNotFound,
)


class DBClusterSnapshot(TaggableRDSResource, BaseRDSModel):

    resource_type = "cluster-snapshot"

    def __init__(
        self, backend, identifier, db_cluster, snapshot_type="manual", tags=None
    ):
        super(DBClusterSnapshot, self).__init__(backend)
        self.db_cluster_snapshot_identifier = identifier
        self.snapshot_type = snapshot_type
        self.percent_progress = 100
        self.status = "available"
        if tags:
            self.add_tags(tags)
        self.cluster = copy.copy(db_cluster)
        self.allocated_storage = self.cluster.allocated_storage
        self.cluster_create_time = self.cluster.created
        self.db_cluster_identifier = self.cluster.resource_id
        self.encrypted = self.cluster.storage_encrypted
        self.engine = self.cluster.engine
        self.engine_version = self.cluster.engine_version
        self.master_username = self.cluster.master_username
        self.port = self.cluster.port
        self.storage_encrypted = self.cluster.storage_encrypted

    @property
    def resource_id(self):
        return self.db_cluster_snapshot_identifier

    @property
    def db_cluster_snapshot_arn(self):
        return self.arn

    @property
    def snapshot_create_time(self):
        return self.created


class DBClusterSnapshotBackend(BaseRDSBackend):
    def __init__(self):
        super(DBClusterSnapshotBackend, self).__init__()
        self.db_cluster_snapshots = OrderedDict()

    def get_db_cluster_snapshot(self, db_cluster_snapshot_identifier):
        if db_cluster_snapshot_identifier in self.db_cluster_snapshots:
            return self.db_cluster_snapshots[db_cluster_snapshot_identifier]
        raise DBClusterSnapshotNotFound(db_cluster_snapshot_identifier)

    def create_db_cluster_snapshot(
        self,
        db_cluster_identifier,
        db_cluster_snapshot_identifier,
        tags=None,
        snapshot_type="manual",
    ):
        if db_cluster_snapshot_identifier in self.db_cluster_snapshots:
            raise DBClusterSnapshotAlreadyExists()
        db_cluster = self.get_db_cluster(db_cluster_identifier)
        snapshot = DBClusterSnapshot(
            self, db_cluster_snapshot_identifier, db_cluster, snapshot_type, tags
        )
        self.db_cluster_snapshots[db_cluster_snapshot_identifier] = snapshot
        return snapshot

    def delete_db_cluster_snapshot(self, db_cluster_snapshot_identifier):
        snapshot = self.get_db_cluster_snapshot(db_cluster_snapshot_identifier)
        return self.db_cluster_snapshots.pop(snapshot.resource_id)

    def describe_db_cluster_snapshots(
        self,
        db_cluster_identifier=None,
        db_cluster_snapshot_identifier=None,
        snapshot_type=None,
        **kwargs
    ):
        if db_cluster_snapshot_identifier:
            return [self.get_db_cluster_snapshot(db_cluster_snapshot_identifier)]
        snapshot_types = (
            ["automated", "manual"] if snapshot_type is None else [snapshot_type]
        )
        if db_cluster_identifier:
            db_cluster_snapshots = []
            for snapshot in self.db_cluster_snapshots.values():
                if snapshot.db_cluster_identifier == db_cluster_identifier:
                    if snapshot.snapshot_type in snapshot_types:
                        db_cluster_snapshots.append(snapshot)
            return db_cluster_snapshots
        return self.db_cluster_snapshots.values()
