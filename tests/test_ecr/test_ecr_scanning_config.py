import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

ECR_REGION = "us-east-1"
ECR_REPO = "test-repo"


@mock_aws
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


@mock_aws
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
            "scanFrequency": "MANUAL",
            "appliedScanFilters": [],
        }
    ]


@mock_aws
def test_registry_scanning_configuration_lifecycle():
    client = boto3.client("ecr", region_name=ECR_REGION)
    client.create_repository(repositoryName=ECR_REPO)

    get_scanning_config_response = client.get_registry_scanning_configuration()
    assert get_scanning_config_response["registryId"] == ACCOUNT_ID
    assert get_scanning_config_response["scanningConfiguration"] == {
        "rules": [],
        "scanType": "BASIC",
    }

    put_scanning_config_response = client.put_registry_scanning_configuration(
        scanType="BASIC",
        rules=[
            {
                "repositoryFilters": [
                    {
                        "filter": "test-*",
                        "filterType": "WILDCARD",
                    }
                ],
                "scanFrequency": "SCAN_ON_PUSH",
            }
        ],
    )

    assert put_scanning_config_response["registryScanningConfiguration"] == {
        "rules": [
            {
                "repositoryFilters": [{"filter": "test-*", "filterType": "WILDCARD"}],
                "scanFrequency": "SCAN_ON_PUSH",
            }
        ],
        "scanType": "BASIC",
    }

    # check if scanning config is returned in get operation
    get_scanning_config_response = client.get_registry_scanning_configuration()
    assert get_scanning_config_response["registryId"] == ACCOUNT_ID
    assert get_scanning_config_response["scanningConfiguration"] == {
        "rules": [
            {
                "repositoryFilters": [{"filter": "test-*", "filterType": "WILDCARD"}],
                "scanFrequency": "SCAN_ON_PUSH",
            }
        ],
        "scanType": "BASIC",
    }

    # check if the scanning config is returned in batch_get_repository_scanning_configuration
    repo_scanning_config_result = client.batch_get_repository_scanning_configuration(
        repositoryNames=[ECR_REPO]
    )
    assert repo_scanning_config_result["scanningConfigurations"][0] == {
        "appliedScanFilters": [{"filter": "test-*", "filterType": "WILDCARD"}],
        "repositoryArn": f"arn:aws:ecr:{ECR_REGION}:{ACCOUNT_ID}:repository/{ECR_REPO}",
        "repositoryName": ECR_REPO,
        "scanFrequency": "SCAN_ON_PUSH",
        "scanOnPush": False,
    }

    # create new repository and check if scanning config is applied
    client.create_repository(repositoryName="test-repo-2")
    repo_scanning_config_result = client.batch_get_repository_scanning_configuration(
        repositoryNames=["test-repo-2"]
    )
    assert repo_scanning_config_result["scanningConfigurations"][0] == {
        "appliedScanFilters": [{"filter": "test-*", "filterType": "WILDCARD"}],
        "repositoryArn": f"arn:aws:ecr:{ECR_REGION}:{ACCOUNT_ID}:repository/test-repo-2",
        "repositoryName": "test-repo-2",
        "scanFrequency": "SCAN_ON_PUSH",
        "scanOnPush": False,
    }

    # revert scanning config and see if it is properly applied to all repositories
    put_scanning_config_response = client.put_registry_scanning_configuration(
        scanType="BASIC",
        rules=[],
    )
    assert put_scanning_config_response["registryScanningConfiguration"] == {
        "rules": [],
        "scanType": "BASIC",
    }

    get_scanning_config_response = client.get_registry_scanning_configuration()
    assert get_scanning_config_response["registryId"] == ACCOUNT_ID
    assert get_scanning_config_response["scanningConfiguration"] == {
        "rules": [],
        "scanType": "BASIC",
    }

    repo_scanning_config_result = client.batch_get_repository_scanning_configuration(
        repositoryNames=[ECR_REPO, "test-repo-2"]
    )
    assert repo_scanning_config_result["scanningConfigurations"] == [
        {
            "appliedScanFilters": [],
            "repositoryArn": f"arn:aws:ecr:{ECR_REGION}:{ACCOUNT_ID}:repository/{ECR_REPO}",
            "repositoryName": ECR_REPO,
            "scanFrequency": "MANUAL",
            "scanOnPush": False,
        },
        {
            "appliedScanFilters": [],
            "repositoryArn": f"arn:aws:ecr:{ECR_REGION}:{ACCOUNT_ID}:repository/test-repo-2",
            "repositoryName": "test-repo-2",
            "scanFrequency": "MANUAL",
            "scanOnPush": False,
        },
    ]
