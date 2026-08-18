.. _implementedservice_payment-cryptography:

====================
payment-cryptography
====================

.. autoclass:: moto.paymentcryptography.models.PaymentCryptographyControlPlaneBackend

Implemented features
--------------------

- [X] add_key_replication_regions
- [X] associate_mpa_team
- [X] create_alias
- [X] create_key
- [X] delete_alias
- [X] delete_key
- [X] delete_resource_policy
- [X] disable_default_key_replication_regions
- [X] disassociate_mpa_team
- [X] enable_default_key_replication_regions
- [X] export_key
- [X] get_alias
- [X] get_certificate_signing_request
- [X] get_default_key_replication_regions
- [X] get_key
- [X] get_mpa_team_association
- [X] get_parameters_for_export
- [X] get_parameters_for_import
- [X] get_public_key_certificate
- [X] get_resource_policy
- [X] import_key
- [X] list_aliases
- [X] list_keys
- [X] list_tags_for_resource
- [X] put_resource_policy
- [X] remove_key_replication_regions
- [X] restore_key
- [X] start_key_usage
- [X] stop_key_usage
- [X] tag_resource
- [X] untag_resource
- [X] update_alias

The control plane stores key material only to preserve coherent state for future
data-plane support. Import and export responses are suitable for mocked workflows;
they do not emulate an AWS hardware security module or provide TR-31/TR-34
interoperability guarantees.
