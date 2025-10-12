import json

import boto3
import requests

from moto import mock_aws, settings
from tests import DEFAULT_ACCOUNT_ID

from .test_ecr_helpers import _create_image_manifest

example_response = {
    "imageScanFindings": {
        "enhancedFindings": [
            {
                "awsAccountId": DEFAULT_ACCOUNT_ID,
                "description": "When curl is asked to use HSTS, the expiry time for a subdomain might overwrite a parent domain's cache entry, making it end sooner or later than otherwise intended. This affects curl using applications that enable HSTS and use URLs with the insecure `HTTP://` scheme and perform transfers with hosts like `x.example.com` as well as `example.com` where the first host is a subdomain of the second host. (The HSTS cache either needs to have been populated manually or there needs to have been previous HTTPS accesses done as the cache needs to have entries for the domains involved to trigger this problem.) When `x.example.com` responds with `Strict-Transport-Security:` headers, this bug can make the subdomain's expiry timeout *bleed over* and get set for the parent domain `example.com` in curl's HSTS cache. The result of a triggered bug is that HTTP accesses to `example.com` get converted to HTTPS for a different period of time than what was asked for by the origin server. If `example.com` for example stops supporti",
                "findingArn": "arn:aws:inspector2:eu-west-1:000000000000:finding/92ec736dde6c50c668cf5721027ae176",
                "packageVulnerabilityDetails": {
                    "cvss": [
                        {
                            "baseScore": 6.5,
                            "scoringVector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:L",
                            "source": "NVD",
                            "version": "3.1",
                        }
                    ],
                    "referenceUrls": [
                        "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1086804"
                    ],
                    "relatedVulnerabilities": [],
                    "source": "DEBIAN_CVE",
                    "sourceUrl": "https://security-tracker.debian.org/tracker/CVE-2024-9681",
                    "vendorSeverity": "not yet assigned",
                    "vulnerabilityId": "CVE-2024-9681",
                    "vulnerablePackages": [
                        {
                            "arch": "AMD64",
                            "epoch": 0,
                            "name": "curl",
                            "packageManager": "OS",
                            "release": "10+deb12u8",
                            "sourceLayerHash": "sha256:416e17e4fbb3912125a75f472458c684de6c08405c5c0d2221649b7feac4f78c",
                            "version": "7.88.1",
                            "fixedInVersion": "NotAvailable",
                        }
                    ],
                },
                "remediation": {"recommendation": {"text": "None Provided"}},
                "resources": [
                    {
                        "details": {
                            "awsEcrContainerImage": {
                                "architecture": "amd64",
                                "imageHash": "sha256:9c7d02b8b260fa42b14a85cc1221f942f2029b5bf1132fc300ec479273406f5d",
                                "imageTags": ["5.0.28"],
                                "platform": "DEBIAN_12",
                                "registry": DEFAULT_ACCOUNT_ID,
                                "repositoryName": "prod/cp/motoserver",
                            }
                        },
                        "id": "arn:aws:ecr:eu-west-1:000000000000:repository/prod/cp/motoserver/sha256:9c7d02b8b260fa42b14a85cc1221f942f2029b5bf1132fc300ec479273406f5d",
                        "tags": {},
                        "type": "AWS_ECR_CONTAINER_IMAGE",
                    }
                ],
                "score": 6.5,
                "scoreDetails": {
                    "cvss": {
                        "adjustments": [],
                        "score": 6.5,
                        "scoreSource": "NVD",
                        "scoringVector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:L",
                        "version": "3.1",
                    }
                },
                "severity": "MEDIUM",
                "status": "ACTIVE",
                "title": "CVE-2024-9681 - curl",
                "type": "PACKAGE_VULNERABILITY",
                "fixAvailable": "NO",
                "exploitAvailable": "NO",
            },
            {
                "awsAccountId": DEFAULT_ACCOUNT_ID,
                "description": "None Provided",
                "findingArn": "arn:aws:inspector2:eu-west-1:000000000000:finding/9ff1469a4702529c61a8f00661a27576",
                "packageVulnerabilityDetails": {
                    "cvss": [],
                    "referenceUrls": [
                        "https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1094730"
                    ],
                    "relatedVulnerabilities": [],
                    "source": "DEBIAN_CVE",
                    "sourceUrl": "https://security-tracker.debian.org/tracker/CVE-2025-24528",
                    "vendorSeverity": "not yet assigned",
                    "vulnerabilityId": "CVE-2025-24528",
                    "vulnerablePackages": [
                        {
                            "arch": "AMD64",
                            "epoch": 0,
                            "name": "krb5",
                            "packageManager": "OS",
                            "release": "2+deb12u2",
                            "sourceLayerHash": "sha256:951ef04389205caf59aa51717bdd03e0765e97a42bd488de11ebe7b05db2b525",
                            "version": "1.20.1",
                            "fixedInVersion": "NotAvailable",
                        }
                    ],
                },
                "remediation": {"recommendation": {"text": "None Provided"}},
                "resources": [
                    {
                        "details": {
                            "awsEcrContainerImage": {
                                "architecture": "amd64",
                                "imageHash": "sha256:9c7d02b8b260fa42b14a85cc1221f942f2029b5bf1132fc300ec479273406f5d",
                                "imageTags": ["5.0.28"],
                                "platform": "DEBIAN_12",
                                "registry": DEFAULT_ACCOUNT_ID,
                                "repositoryName": "prod/cp/motoserver",
                            }
                        },
                        "id": "arn:aws:ecr:eu-west-1:000000000000:repository/prod/cp/motoserver/sha256:9c7d02b8b260fa42b14a85cc1221f942f2029b5bf1132fc300ec479273406f5d",
                        "tags": {},
                        "type": "AWS_ECR_CONTAINER_IMAGE",
                    }
                ],
                "score": 0.0,
                "severity": "UNTRIAGED",
                "status": "ACTIVE",
                "title": "CVE-2025-24528 - krb5",
                "type": "PACKAGE_VULNERABILITY",
                "fixAvailable": "NO",
                "exploitAvailable": "NO",
            },
        ],
        "findingSeverityCounts": {"MEDIUM": 1, "UNTRIAGED": 1},
    },
    "registryId": DEFAULT_ACCOUNT_ID,
    "repositoryName": "reponame",
    "imageId": {"imageTag": "latest"},
    "imageScanStatus": {
        "status": "COMPLETE",
        "description": "The scan was completed successfully.",
    },
}


@mock_aws
def test_set_findings():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    findings = {
        "results": [example_response],
        "region": "us-west-1",
    }
    resp = requests.post(
        f"http://{base_url}/moto-api/static/ecr/scan-finding-results",
        json=findings,
    )
    assert resp.status_code == 201

    ecr = boto3.client("ecr", region_name="us-west-1")
    ecr.create_repository(repositoryName="reponame")
    image_tag = "latest"
    image_digest = ecr.put_image(
        repositoryName="reponame",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag=image_tag,
    )["image"]["imageId"]["imageDigest"]

    # Diversion
    ecr.create_repository(repositoryName="reponame2")
    ecr.put_image(
        repositoryName="reponame2",
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag="latest",
    )
    ecr.start_image_scan(repositoryName="reponame2", imageId={"imageTag": "latest"})

    # when
    ecr.start_image_scan(repositoryName="reponame", imageId={"imageTag": image_tag})

    findings = ecr.describe_image_scan_findings(
        repositoryName="reponame", imageId={"imageTag": image_tag}
    )
    findings.pop("ResponseMetadata")
    assert findings == example_response

    # Retrieving results for different repo returns the default response
    diff_findings = ecr.describe_image_scan_findings(
        repositoryName="reponame2", imageId={"imageTag": image_tag}
    )
    assert diff_findings["imageScanFindings"]["findingSeverityCounts"]["HIGH"] == 1

    # Retrieving results using imageDigest also returns the default (because it's not configured)
    diff_findings = ecr.describe_image_scan_findings(
        repositoryName="reponame", imageId={"imageDigest": image_digest}
    )
    assert diff_findings["imageScanFindings"]["findingSeverityCounts"]["HIGH"] == 1

    # Calling list_findings with original arguments returns original list
    findings = ecr.describe_image_scan_findings(
        repositoryName="reponame", imageId={"imageTag": image_tag}
    )
    findings.pop("ResponseMetadata")
    assert findings == example_response
