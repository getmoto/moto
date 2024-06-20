.. _implementedservice_resiliencehub:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
resiliencehub
=============

|start-h3| Implemented features for this service |end-h3|

- [ ] add_draft_app_version_resource_mappings
- [ ] batch_update_recommendation_status
- [X] create_app
  
        The ClientToken-parameter is not yet implemented
        

- [X] create_app_version_app_component
- [X] create_app_version_resource
- [ ] create_recommendation_template
- [X] create_resiliency_policy
  
        The ClientToken-parameter is not yet implemented
        

- [ ] delete_app
- [ ] delete_app_assessment
- [ ] delete_app_input_source
- [ ] delete_app_version_app_component
- [ ] delete_app_version_resource
- [ ] delete_recommendation_template
- [ ] delete_resiliency_policy
- [X] describe_app
- [ ] describe_app_assessment
- [ ] describe_app_version
- [ ] describe_app_version_app_component
- [ ] describe_app_version_resource
- [ ] describe_app_version_resources_resolution_status
- [ ] describe_app_version_template
- [ ] describe_draft_app_version_resources_import_status
- [X] describe_resiliency_policy
- [X] import_resources_to_draft_app_version
- [ ] list_alarm_recommendations
- [ ] list_app_assessment_compliance_drifts
- [X] list_app_assessments
  
        Moto will not actually execute any assessments, so this operation will return an empty list by default.
        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `list_app_assessments` will take the first result from that queue, with subsequent calls with the same parameters returning the same result.

        Calling `list_app_assessments` with a different set of parameters will return the second result from that queue - and so on, or an empty list of the queue is empty.

        Configure this queue by making an HTTP request to `/moto-api/static/resilience-hub-assessments/response`. An example invocation looks like this:

        .. sourcecode:: python

            summary1 = {"appArn": "app_arn1", "appVersion": "some version", ...}
            summary2 = {"appArn": "app_arn2", ...}
            results = {"results": [[summary1, summary2], [summary2]], "region": "us-east-1"}
            resp = requests.post(
                "http://motoapi.amazonaws.com/moto-api/static/resilience-hub-assessments/response",
                json=results,
            )

            assert resp.status_code == 201

            client = boto3.client("lambda", region_name="us-east-1")
            # First result
            resp = client.list_app_assessments() # [summary1, summary2]
            # Second result
            resp = client.list_app_assessments(assessmentStatus="Pending") # [summary2]

        If you're using MotoServer, make sure to make this request to where MotoServer is running:

        .. sourcecode:: python

            http://localhost:5000/moto-api/static/resilience-hub-assessments/response

        

- [ ] list_app_component_compliances
- [ ] list_app_component_recommendations
- [ ] list_app_input_sources
- [X] list_app_version_app_components
- [ ] list_app_version_resource_mappings
- [X] list_app_version_resources
- [X] list_app_versions
- [X] list_apps
  
        The FromAssessmentTime/ToAssessmentTime-parameters are not yet implemented
        

- [ ] list_recommendation_templates
- [X] list_resiliency_policies
- [ ] list_sop_recommendations
- [ ] list_suggested_resiliency_policies
- [X] list_tags_for_resource
- [ ] list_test_recommendations
- [ ] list_unsupported_app_version_resources
- [X] publish_app_version
- [ ] put_draft_app_version_template
- [ ] remove_draft_app_version_resource_mappings
- [ ] resolve_app_version_resources
- [ ] start_app_assessment
- [X] tag_resource
- [X] untag_resource
- [ ] update_app
- [ ] update_app_version
- [ ] update_app_version_app_component
- [ ] update_app_version_resource
- [ ] update_resiliency_policy

