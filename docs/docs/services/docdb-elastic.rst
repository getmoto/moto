.. _implementedservice_docdb-elastic:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
docdb-elastic
=============

.. autoclass:: moto.docdbelastic.models.DocDBElasticBackend

|start-h3| Implemented features for this service |end-h3|

- [X] apply_pending_maintenance_action
  
Pending maintenance actions are never scheduled by Moto, so this
is a no-op that validates the resource exists.


- [X] copy_cluster_snapshot
- [X] create_cluster
- [X] create_cluster_snapshot
- [X] delete_cluster
- [X] delete_cluster_snapshot
- [X] get_cluster
- [X] get_cluster_snapshot
- [X] get_pending_maintenance_action
  
Pending maintenance actions are never scheduled by Moto, so this
always returns an empty list of actions for an existing resource.


- [X] list_cluster_snapshots
- [X] list_clusters
- [X] list_pending_maintenance_actions
  
Pending maintenance actions are never scheduled by Moto, so this
always returns an empty list. Pagination is not yet implemented.


- [X] list_tags_for_resource
- [X] restore_cluster_from_snapshot
- [X] start_cluster
- [X] stop_cluster
- [X] tag_resource
- [X] untag_resource
- [X] update_cluster

