import boto3
from moto import mock_ecr


@mock_ecr
def test_batch_get_repository_scanning_configuration():
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"
    repo_arn = client.create_repository(repositoryName=repo_name)["repository"][
        "repositoryArn"
    ]

    # Default ScanningConfig is returned
    resp = client.batch_get_repository_scanning_configuration(
        repositoryNames=[repo_name]
    )

    assert resp["scanningConfigurations"] == [
        {
            "repositoryArn": repo_arn,
            "repositoryName": repo_name,
            "scanOnPush": False,
            "scanFrequency": "MANUAL",
            "appliedScanFilters": [],
        }
    ]
    assert resp["failures"] == []

    # Non-existing repositories are returned as failures
    resp = client.batch_get_repository_scanning_configuration(
        repositoryNames=["unknown"]
    )

    assert resp["scanningConfigurations"] == []
    assert resp["failures"] == [
        {
            "repositoryName": "unknown",
            "failureCode": "REPOSITORY_NOT_FOUND",
            "failureReason": "REPOSITORY_NOT_FOUND",
        }
    ]


@mock_ecr
def test_put_registry_scanning_configuration():
    client = boto3.client("ecr", region_name="us-east-1")
    repo_name = "test-repo"
    repo_arn = client.create_repository(repositoryName=repo_name)["repository"][
        "repositoryArn"
    ]

    #####
    # Creating a ScanningConfig where
    #      filter == repo_name
    ####
    client.put_registry_scanning_configuration(
        scanType="ENHANCED",
        rules=[
            {
                "scanFrequency": "CONTINUOUS_SCAN",
                "repositoryFilters": [{"filter": repo_name, "filterType": "WILDCARD"}],
            }
        ],
    )

    resp = client.batch_get_repository_scanning_configuration(
        repositoryNames=[repo_name]
    )

    assert resp["scanningConfigurations"] == [
        {
            "repositoryArn": repo_arn,
            "repositoryName": repo_name,
            "scanOnPush": False,
            "scanFrequency": "CONTINUOUS_SCAN",
            "appliedScanFilters": [{"filter": repo_name, "filterType": "WILDCARD"}],
        }
    ]

    #####
    # Creating a ScanningConfig where
    #      filter == repo*
    ####
    client.put_registry_scanning_configuration(
        scanType="ENHANCED",
        rules=[
            {
                "scanFrequency": "SCAN_ON_PUSH",
                "repositoryFilters": [
                    {"filter": f"{repo_name[:4]}*", "filterType": "WILDCARD"}
                ],
            }
        ],
    )

    resp = client.batch_get_repository_scanning_configuration(
        repositoryNames=[repo_name]
    )

    assert resp["scanningConfigurations"] == [
        {
            "repositoryArn": repo_arn,
            "repositoryName": repo_name,
            "scanOnPush": False,
            "scanFrequency": "SCAN_ON_PUSH",
            "appliedScanFilters": [
                {"filter": f"{repo_name[:4]}*", "filterType": "WILDCARD"}
            ],
        }
    ]

    #####
    # Creating a ScanningConfig where
    #      filter == unknown_repo
    ####
    client.put_registry_scanning_configuration(
        scanType="ENHANCED",
        rules=[
            {
                "scanFrequency": "MANUAL",
                "repositoryFilters": [{"filter": "unknown", "filterType": "WILDCARD"}],
            }
        ],
    )

    resp = client.batch_get_repository_scanning_configuration(
        repositoryNames=[repo_name]
    )

    assert resp["scanningConfigurations"] == [
        {
            "repositoryArn": repo_arn,
            "repositoryName": repo_name,
            "scanOnPush": False,
            "scanFrequency": "SCAN_ON_PUSH",
            "appliedScanFilters": [
                {"filter": f"{repo_name[:4]}*", "filterType": "WILDCARD"}
            ],
        }
    ]
