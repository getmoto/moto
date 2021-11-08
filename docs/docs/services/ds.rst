.. _implementedservice_ds:

==
ds
==

Implementation of DirectoryService APIs.

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

- [ ] create_log_subscription
- [X] create_microsoft_ad
  Create a fake Microsoft Ad Directory.

- [ ] create_snapshot
- [ ] create_trust
- [ ] delete_conditional_forwarder
- [X] delete_directory
  Delete directory with the matching ID.

- [ ] delete_log_subscription
- [ ] delete_snapshot
- [ ] delete_trust
- [ ] deregister_certificate
- [ ] deregister_event_topic
- [ ] describe_certificate
- [ ] describe_client_authentication_settings
- [ ] describe_conditional_forwarders
- [X] describe_directories
  Return info on all directories or directories with matching IDs.

- [ ] describe_domain_controllers
- [ ] describe_event_topics
- [ ] describe_ldaps_settings
- [ ] describe_regions
- [ ] describe_shared_directories
- [ ] describe_snapshots
- [ ] describe_trusts
- [ ] disable_client_authentication
- [ ] disable_ldaps
- [ ] disable_radius
- [X] disable_sso
  Disable single-sign on for a directory.

- [ ] enable_client_authentication
- [ ] enable_ldaps
- [ ] enable_radius
- [X] enable_sso
  Enable single-sign on for a directory.

- [X] get_directory_limits
  Return hard-coded limits for the directories.

- [ ] get_snapshot_limits
- [ ] list_certificates
- [ ] list_ip_routes
- [ ] list_log_subscriptions
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
- [ ] start_schema_extension
- [ ] unshare_directory
- [ ] update_conditional_forwarder
- [ ] update_number_of_domain_controllers
- [ ] update_radius
- [ ] update_trust
- [ ] verify_trust

