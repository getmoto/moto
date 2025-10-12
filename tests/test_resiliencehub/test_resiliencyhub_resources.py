import boto3

from moto import mock_aws


@mock_aws
def test_import_resources_to_draft_app_version():
    client = boto3.client("resiliencehub", region_name="us-east-2")
    app_arn = client.create_app(name="myapp")["app"]["appArn"]

    components = client.list_app_version_app_components(
        appArn=app_arn, appVersion="draft"
    )
    assert components["appArn"] == app_arn
    assert components["appComponents"] == []
    assert components["appVersion"] == "draft"

    resp = client.import_resources_to_draft_app_version(
        appArn=app_arn,
        eksSources=[{"eksClusterArn": "some-arn", "namespaces": ["eks/ns/1"]}],
        importStrategy="AddOnly",
        sourceArns=["sarn1", "sarn2"],
        terraformSources=[{"s3StateFileUrl": "tf://url"}],
    )
    assert resp["appArn"] == app_arn
    assert resp["eksSources"] == [
        {"eksClusterArn": "some-arn", "namespaces": ["eks/ns/1"]}
    ]
    assert resp["sourceArns"] == ["sarn1", "sarn2"]
    assert resp["status"] == "Pending"
    assert resp["terraformSources"] == [{"s3StateFileUrl": "tf://url"}]

    components = client.list_app_version_app_components(
        appArn=app_arn, appVersion="draft"
    )["appComponents"]
    assert {
        "id": "appcommon",
        "name": "appcommon",
        "type": "AWS::ResilienceHub::AppCommonAppComponent",
    } in components


@mock_aws
def test_create_app_version_app_component():
    client = boto3.client("resiliencehub", region_name="us-east-2")
    app_arn = client.create_app(name="myapp")["app"]["appArn"]
    component = client.create_app_version_app_component(
        appArn=app_arn,
        name="my_databases",
        type="AWS::ResilienceHub::DatabaseAppComponent",
    )
    assert component["appArn"] == app_arn
    assert component["appVersion"] == "draft"
    assert component["appComponent"]["id"] == "my_databases"
    assert component["appComponent"]["name"] == "my_databases"
    assert (
        component["appComponent"]["type"] == "AWS::ResilienceHub::DatabaseAppComponent"
    )

    components = client.list_app_version_app_components(
        appArn=app_arn, appVersion="draft"
    )["appComponents"]
    assert components == [
        {
            "id": "my_databases",
            "name": "my_databases",
            "type": "AWS::ResilienceHub::DatabaseAppComponent",
        }
    ]


@mock_aws
def test_create_app_version_resource():
    client = boto3.client("resiliencehub", region_name="us-east-2")
    app_arn = client.create_app(name="myapp")["app"]["appArn"]

    component = client.create_app_version_app_component(
        appArn=app_arn,
        name="my_databases",
        type="AWS::ResilienceHub::DatabaseAppComponent",
    )["appComponent"]

    resp = client.create_app_version_resource(
        appArn=app_arn,
        appComponents=["my_databases"],
        logicalResourceId={
            "identifier": "myres",
        },
        physicalResourceId="myphys",
        resourceType="AWS::Lambda::Function",
    )
    assert resp["appArn"] == app_arn
    assert resp["appVersion"] == "draft"
    assert resp["physicalResource"]["appComponents"] == [component]
    assert resp["physicalResource"]["logicalResourceId"] == {"identifier": "myres"}
    assert resp["physicalResource"]["physicalResourceId"]["identifier"] == "myphys"
    assert resp["physicalResource"]["resourceName"] == "myres"
    assert resp["physicalResource"]["resourceType"] == "AWS::Lambda::Function"

    resources = client.list_app_version_resources(appArn=app_arn, appVersion="draft")
    assert resources["physicalResources"] == [resp["physicalResource"]]


@mock_aws
def test_create_app_version_resource_with_unknown_component():
    client = boto3.client("resiliencehub", region_name="us-east-2")
    app_arn = client.create_app(name="myapp")["app"]["appArn"]

    # Not sure how AWS behaves, when providing an unknown appComponent
    # But let's try to be flexible in what we accept
    resp = client.create_app_version_resource(
        appArn=app_arn,
        appComponents=["unknown"],
        logicalResourceId={
            "identifier": "myres",
        },
        physicalResourceId="myphys",
        resourceType="AWS::Lambda::Function",
    )
    assert resp["physicalResource"]["appComponents"] == []


@mock_aws
def test_publish():
    client = boto3.client("resiliencehub", region_name="us-east-2")
    app_arn = client.create_app(name="myapp")["app"]["appArn"]

    versions = client.list_app_versions(appArn=app_arn)["appVersions"]
    assert len(versions) == 1
    assert versions[0]["appVersion"] == "draft"
    assert versions[0]["creationTime"]
    assert versions[0]["identifier"] == 0

    client.import_resources_to_draft_app_version(
        appArn=app_arn,
        eksSources=[{"eksClusterArn": "some-arn", "namespaces": ["eks/ns/1"]}],
        importStrategy="AddOnly",
        sourceArns=["sarn1", "sarn2"],
        terraformSources=[{"s3StateFileUrl": "tf://url"}],
    )

    publish = client.publish_app_version(appArn=app_arn, versionName="v1")
    assert publish["appArn"] == app_arn
    assert publish["appVersion"] == "release"
    assert publish["identifier"] == 1
    assert publish["versionName"] == "v1"

    versions = client.list_app_versions(appArn=app_arn)["appVersions"]
    assert len(versions) == 2
    assert versions[1]["appVersion"] == "release"
    assert versions[1]["identifier"] == 1
    assert versions[1]["versionName"] == "v1"

    client.publish_app_version(appArn=app_arn, versionName="v2")

    versions = client.list_app_versions(appArn=app_arn)["appVersions"]
    assert len(versions) == 3
    for v in versions:
        del v["creationTime"]

    assert {"appVersion": "release", "identifier": 2, "versionName": "v2"} in versions
    assert {"appVersion": "1", "identifier": 1, "versionName": "v1"} in versions
