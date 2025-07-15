.. _implementedservice_inspector2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
inspector2
==========

|start-h3| Implemented features for this service |end-h3|

- [X] associate_member
- [ ] batch_associate_code_security_scan_configuration
- [ ] batch_disassociate_code_security_scan_configuration
- [X] batch_get_account_status
- [ ] batch_get_code_snippet
- [ ] batch_get_finding_details
- [ ] batch_get_free_trial_info
- [ ] batch_get_member_ec2_deep_inspection_status
- [ ] batch_update_member_ec2_deep_inspection_status
- [ ] cancel_findings_report
- [ ] cancel_sbom_export
- [ ] create_cis_scan_configuration
- [ ] create_code_security_integration
- [ ] create_code_security_scan_configuration
- [X] create_filter
- [ ] create_findings_report
- [ ] create_sbom_export
- [ ] delete_cis_scan_configuration
- [ ] delete_code_security_integration
- [ ] delete_code_security_scan_configuration
- [X] delete_filter
- [X] describe_organization_configuration
- [X] disable
- [X] disable_delegated_admin_account
- [X] disassociate_member
- [X] enable
- [X] enable_delegated_admin_account
- [ ] get_cis_scan_report
- [ ] get_cis_scan_result_details
- [ ] get_clusters_for_image
- [ ] get_code_security_integration
- [ ] get_code_security_scan
- [ ] get_code_security_scan_configuration
- [ ] get_configuration
- [ ] get_delegated_admin_account
- [ ] get_ec2_deep_inspection_configuration
- [ ] get_encryption_key
- [ ] get_findings_report_status
- [X] get_member
- [ ] get_sbom_export
- [ ] list_account_permissions
- [ ] list_cis_scan_configurations
- [ ] list_cis_scan_results_aggregated_by_checks
- [ ] list_cis_scan_results_aggregated_by_target_resource
- [ ] list_cis_scans
- [ ] list_code_security_integrations
- [ ] list_code_security_scan_configuration_associations
- [ ] list_code_security_scan_configurations
- [ ] list_coverage
- [ ] list_coverage_statistics
- [X] list_delegated_admin_accounts
- [X] list_filters
  
        Pagination is not yet implemented
        

- [ ] list_finding_aggregations
- [X] list_findings
  
        This call will always return 0 findings by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `list_findings` will take the first result from that queue, and assign it to the provided arguments. Subsequent calls using the same arguments will return the same result. Other requests using a different SQL-query will take the next result from the queue, or return an empty result if the queue is empty.

        Configure this queue by making an HTTP request to `/moto-api/static/inspector2/findings-results`. An example invocation looks like this:

        .. sourcecode:: python

            findings = {
                "results": [
                    [{
                        "awsAccountId": "111122223333",
                        "codeVulnerabilityDetails": {"cwes": ["a"], "detectorId": ".."},
                    }],
                    # .. other findings as required
                ],
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com/moto-api/static/inspector2/findings-results",
                json=findings,
            )

            inspector2 = boto3.client("inspector2", region_name="us-east-1")
            findings = inspector2.list_findings()["findings"]

        

- [X] list_members
- [X] list_tags_for_resource
- [ ] list_usage_totals
- [ ] reset_encryption_key
- [ ] search_vulnerabilities
- [ ] send_cis_session_health
- [ ] send_cis_session_telemetry
- [ ] start_cis_session
- [ ] start_code_security_scan
- [ ] stop_cis_session
- [X] tag_resource
- [X] untag_resource
- [ ] update_cis_scan_configuration
- [ ] update_code_security_integration
- [ ] update_code_security_scan_configuration
- [ ] update_configuration
- [ ] update_ec2_deep_inspection_configuration
- [ ] update_encryption_key
- [ ] update_filter
- [ ] update_org_ec2_deep_inspection_configuration
- [X] update_organization_configuration

