import json
import os
from unittest import SkipTest, mock

import boto3
import responses

from moto import mock_aws, settings


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_EVENTS_INVOKE_HTTP": "true"})
def test_invoke_http_request_on_event():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't intercept HTTP requests in ServerMode")
    events = boto3.client("events", region_name="eu-west-1")

    #
    # Create API endpoint to invoke
    response = events.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    destination_response = events.create_api_destination(
        Name="test",
        Description="test-description",
        ConnectionArn=response.get("ConnectionArn"),
        InvocationEndpoint="https://www.google.com",
        HttpMethod="GET",
    )
    destination_arn = destination_response["ApiDestinationArn"]

    #
    # Create Rules when to invoke the connection
    pattern = {"source": ["test-source"], "detail-type": ["test-detail-type"]}
    rule_name = "test-event-rule"
    events.put_rule(
        Name=rule_name,
        State="ENABLED",
        EventPattern=json.dumps(pattern),
    )

    events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "123",
                "Arn": destination_arn,
                "HttpParameters": {
                    "HeaderParameters": {"header1": "value1"},
                    "QueryStringParameters": {"qs1": "qv2"},
                },
            }
        ],
    )

    #
    # Ensure we intercept HTTP requests
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        # test that both json and urlencoded body are empty in matcher and in request
        rsps.add(
            method=responses.GET,
            url="https://www.google.com/",
            match=[
                responses.matchers.header_matcher({"header1": "value1"}),
                responses.matchers.query_param_matcher({"qs1": "qv2"}),
            ],
        )

        #
        # Invoke HTTP requests
        events.put_events(
            Entries=[
                {
                    "Source": "test-source",
                    "DetailType": "test-detail-type",
                    "Detail": "{}",
                }
            ]
        )
