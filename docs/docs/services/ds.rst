.. _implementedservice_ds:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==
ds
==

.. autoclass:: moto.ds.models.DirectoryServiceBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] accept_shared_directory
- [ ] add_ip_routes
- [ ] add_region
- [X] add_tags_to_resource
  Add or overwrite one or more tags for specified directory.

- [ ] cancel_schema_extension
- [X] connect_directory
  Create a fake AD Connector.

- [X] create_alias
  Create and assign an alias to a directory.

- [ ] create_computer
- [ ] create_conditional_forwarder
- [X] create_directory
  Create a fake Simple Ad Directory.

- [ ] create_hybrid_ad
- [X] create_log_subscription
- [X] create_microsoft_ad
  Create a fake Microsoft Ad Directory.

- [ ] create_snapshot
- [X] create_trust
- [ ] delete_ad_assessment
- [ ] delete_conditional_forwarder
- [X] delete_directory
  Delete directory with the matching ID.

- [X] delete_log_subscription
- [ ] delete_snapshot
- [X] delete_trust
- [ ] deregister_certificate
- [ ] deregister_event_topic
- [ ] describe_ad_assessment
- [ ] describe_certificate
- [ ] describe_client_authentication_settings
- [ ] describe_conditional_forwarders
- [X] describe_directories
  Return info on all directories or directories with matching IDs.

- [ ] describe_directory_data_access
- [ ] describe_domain_controllers
- [ ] describe_event_topics
- [ ] describe_hybrid_ad_update
- [X] describe_ldaps_settings
  Describe LDAPS settings for a Directory

- [ ] describe_regions
- [X] describe_settings
  Describe settings for a Directory

- [ ] describe_shared_directories
- [ ] describe_snapshots
- [X] describe_trusts
- [ ] describe_update_directory
- [ ] disable_client_authentication
- [ ] disable_directory_data_access
- [X] disable_ldaps
  Disable LDAPS for a Directory

- [ ] disable_radius
- [X] disable_sso
  Disable single-sign on for a directory.

- [ ] enable_client_authentication
- [ ] enable_directory_data_access
- [X] enable_ldaps
  Enable LDAPS for a Directory

- [ ] enable_radius
- [X] enable_sso
  Enable single-sign on for a directory.

- [X] get_directory_limits
  Return hard-coded limits for the directories.

- [ ] get_snapshot_limits
- [ ] list_ad_assessments
- [ ] list_certificates
- [ ] list_ip_routes
- [X] list_log_subscriptions
- [ ] list_schema_extensions
- [X] list_tags_for_resource
  List all tags on a directory.

- [ ] register_certificate
- [ ] register_event_topic
- [ ] reject_shared_directory
- [ ] remove_ip_routes
- [ ] remove_region
- [X] remove_tags_from_resource
  Removes tags from a directory.

- [ ] reset_user_password
- [ ] restore_from_snapshot
- [ ] share_directory
- [ ] start_ad_assessment
- [ ] start_schema_extension
- [ ] unshare_directory
- [ ] update_conditional_forwarder
- [ ] update_directory_setup
- [ ] update_hybrid_ad
- [ ] update_number_of_domain_controllers
- [ ] update_radius
- [X] update_settings
- [ ] update_trust
- [ ] verify_trust

