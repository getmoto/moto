import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from . import cloudfront_test_scaffolding as scaffold


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("us-west-1", "aws"), ("cn-north-1", "aws-cn")]
)
def test_create_distribution_s3_minimum(region, partition):
    client = boto3.client("cloudfront", region_name=region)
    config = scaffold.example_distribution_config("ref")

    dist = client.create_distribution(DistributionConfig=config)["Distribution"]
    assert (
        dist["ARN"]
        == f"arn:{partition}:cloudfront:{ACCOUNT_ID}:distribution/{dist['Id']}"
    )
    assert dist["Status"] == "InProgress"
    assert "LastModifiedTime" in dist
    assert dist["InProgressInvalidationBatches"] == 0
    assert ".cloudfront.net" in dist["DomainName"]

    assert dist["ActiveTrustedSigners"] == {
        "Enabled": False,
        "Items": [],
        "Quantity": 0,
    }

    assert dist["ActiveTrustedKeyGroups"] == {
        "Enabled": False,
        "Items": [],
        "Quantity": 0,
    }

    config = dist["DistributionConfig"]
    assert config["CallerReference"] == "ref"

    assert config["Aliases"]["Quantity"] == 0

    origins = config["Origins"]
    assert origins["Quantity"] == 1
    assert len(origins["Items"]) == 1
    origin = origins["Items"][0]
    assert origin["Id"] == "origin1"
    assert origin["DomainName"] == "asdf.s3.us-east-1.amazonaws.com"
    assert origin["OriginPath"] == "/example"

    assert origin["CustomHeaders"]["Quantity"] == 0

    assert origin["ConnectionAttempts"] == 3
    assert origin["ConnectionTimeout"] == 10
    assert origin["OriginShield"] == {"Enabled": False}

    assert config["OriginGroups"] == {"Quantity": 0}

    default_cache = config["DefaultCacheBehavior"]
    assert default_cache["TargetOriginId"] == "origin1"

    assert default_cache["TrustedSigners"] == {
        "Enabled": False,
        "Items": [],
        "Quantity": 0,
    }

    assert default_cache["TrustedKeyGroups"] == {
        "Enabled": False,
        "Items": [],
        "Quantity": 0,
    }

    assert default_cache["ViewerProtocolPolicy"] == "allow-all"

    methods = default_cache["AllowedMethods"]
    assert methods["Quantity"] == 2
    assert set(methods["Items"]) == {"HEAD", "GET"}

    cached_methods = methods["CachedMethods"]
    assert cached_methods["Quantity"] == 2
    assert set(cached_methods["Items"]) == {"HEAD", "GET"}

    assert default_cache["SmoothStreaming"] is False
    assert default_cache["Compress"] is True
    assert default_cache["LambdaFunctionAssociations"] == {"Quantity": 0}
    assert default_cache["FunctionAssociations"] == {"Quantity": 0}
    assert default_cache["FieldLevelEncryptionId"] == ""
    assert "CachePolicyId" in default_cache

    assert config["CacheBehaviors"] == {"Quantity": 0}
    assert config["CustomErrorResponses"] == {"Quantity": 0}
    assert config["Comment"] == "an optional comment that's not actually optional"

    assert config["Logging"] == {
        "Bucket": "",
        "Enabled": False,
        "IncludeCookies": False,
        "Prefix": "",
    }

    assert config["PriceClass"] == "PriceClass_All"
    assert config["Enabled"] is False
    assert "WebACLId" in config
    assert config["HttpVersion"] == "http2"
    assert config["IsIPV6Enabled"] is True

    assert config["ViewerCertificate"] == {
        "ACMCertificateArn": "",
        "Certificate": "",
        "CertificateSource": "cloudfront",
        "CloudFrontDefaultCertificate": True,
        "IAMCertificateId": "",
        "MinimumProtocolVersion": "TLSv1",
        "SSLSupportMethod": "",
    }

    restriction = config["Restrictions"]["GeoRestriction"]
    assert restriction["RestrictionType"] == "none"
    assert restriction["Quantity"] == 0

    assert config["WebACLId"] == ""


@mock_aws
def test_create_distribution_with_logging():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    config["Logging"] = {
        "Enabled": True,
        "IncludeCookies": True,
        "Bucket": "logging-bucket",
        "Prefix": "logging-bucket",
    }

    resp = client.create_distribution(DistributionConfig=config)
    config = resp["Distribution"]["DistributionConfig"]

    assert config["Logging"] == {
        "Bucket": "logging-bucket",
        "Enabled": True,
        "IncludeCookies": True,
        "Prefix": "logging-bucket",
    }


@mock_aws
def test_create_distribution_with_web_acl():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    config["WebACLId"] = "test-web-acl"

    resp = client.create_distribution(DistributionConfig=config)
    config = resp["Distribution"]["DistributionConfig"]

    assert config["WebACLId"] == "test-web-acl"


@mock_aws
def test_create_distribution_with_field_level_encryption_and_real_time_log_config_arn():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    real_time_log_config_arn = f"arn:aws:cloudfront::{ACCOUNT_ID}:realtime-log-config/ExampleNameForRealtimeLogConfig"
    config["DefaultCacheBehavior"]["RealtimeLogConfigArn"] = real_time_log_config_arn
    config["DefaultCacheBehavior"]["FieldLevelEncryptionId"] = "K3D5EWEUDCCXON"

    resp = client.create_distribution(DistributionConfig=config)

    config = resp["Distribution"]["DistributionConfig"]
    default_cache = config["DefaultCacheBehavior"]

    assert default_cache["FieldLevelEncryptionId"] == "K3D5EWEUDCCXON"
    assert default_cache["RealtimeLogConfigArn"] == real_time_log_config_arn


@mock_aws
def test_create_distribution_with_georestriction():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    config["Restrictions"] = {
        "GeoRestriction": {
            "RestrictionType": "whitelist",
            "Quantity": 2,
            "Items": ["GB", "US"],
        }
    }

    resp = client.create_distribution(DistributionConfig=config)
    config = resp["Distribution"]["DistributionConfig"]

    restriction = config["Restrictions"]["GeoRestriction"]
    assert restriction["RestrictionType"] == "whitelist"
    assert restriction["Quantity"] == 2
    assert "US" in restriction["Items"]
    assert "GB" in restriction["Items"]


@mock_aws
def test_create_distribution_with_allowed_methods():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    config["DefaultCacheBehavior"]["AllowedMethods"] = {
        "Quantity": 3,
        "Items": ["GET", "HEAD", "PUT"],
        "CachedMethods": {
            "Quantity": 7,
            "Items": ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        },
    }

    dist = client.create_distribution(DistributionConfig=config)["Distribution"]

    cache = dist["DistributionConfig"]["DefaultCacheBehavior"]

    assert cache["AllowedMethods"] == {
        "CachedMethods": {
            "Items": ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "Quantity": 7,
        },
        "Items": ["GET", "HEAD", "PUT"],
        "Quantity": 3,
    }


@mock_aws
def test_create_distribution_with_origins():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    config["Origins"]["Items"][0]["ConnectionAttempts"] = 1
    config["Origins"]["Items"][0]["ConnectionTimeout"] = 2
    config["Origins"]["Items"][0]["OriginShield"] = {
        "Enabled": True,
        "OriginShieldRegion": "east",
    }

    dist = client.create_distribution(DistributionConfig=config)["Distribution"]

    origin = dist["DistributionConfig"]["Origins"]["Items"][0]
    assert origin["ConnectionAttempts"] == 1
    assert origin["ConnectionTimeout"] == 2
    assert origin["OriginShield"] == {"Enabled": True, "OriginShieldRegion": "east"}


@mock_aws
@pytest.mark.parametrize("nr_of_headers", [1, 2])
def test_create_distribution_with_custom_headers(nr_of_headers):
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    headers = [
        {"HeaderName": f"X-Custom-Header{i}", "HeaderValue": f"v{i}"}
        for i in range(nr_of_headers)
    ]
    config["Origins"]["Items"][0]["CustomHeaders"] = {
        "Quantity": nr_of_headers,
        "Items": headers,
    }

    dist = client.create_distribution(DistributionConfig=config)["Distribution"]

    origin = dist["DistributionConfig"]["Origins"]["Items"][0]
    assert origin["CustomHeaders"] == {"Quantity": nr_of_headers, "Items": headers}


@mock_aws
@pytest.mark.parametrize("compress", [True, False])
@pytest.mark.parametrize("qs", [True, False])
@pytest.mark.parametrize("smooth", [True, False])
@pytest.mark.parametrize("ipv6", [True, False])
@pytest.mark.parametrize("aliases", [["alias1", "alias2"], ["alias1"]])
def test_create_distribution_with_additional_fields(
    compress, qs, smooth, ipv6, aliases
):
    client = boto3.client("cloudfront", region_name="us-west-1")

    config = scaffold.example_distribution_config("ref")
    config["IsIPV6Enabled"] = ipv6
    config["Aliases"] = {"Quantity": 2, "Items": aliases}
    config["DefaultCacheBehavior"]["ForwardedValues"]["Cookies"] = {
        "Forward": "whitelist",
        "WhitelistedNames": {"Quantity": 1, "Items": ["x-amz-header"]},
    }
    config["DefaultCacheBehavior"]["ForwardedValues"]["QueryString"] = qs
    config["DefaultCacheBehavior"]["Compress"] = compress
    config["DefaultCacheBehavior"]["MinTTL"] = 10
    config["DefaultCacheBehavior"]["SmoothStreaming"] = smooth
    config["PriceClass"] = "PriceClass_100"

    resp = client.create_distribution(DistributionConfig=config)
    config = resp["Distribution"]["DistributionConfig"]

    assert config["Aliases"] == {"Items": aliases, "Quantity": len(aliases)}

    assert config["PriceClass"] == "PriceClass_100"
    assert config["IsIPV6Enabled"] == ipv6

    assert config["DefaultCacheBehavior"]["Compress"] == compress
    assert config["DefaultCacheBehavior"]["MinTTL"] == 10
    assert config["DefaultCacheBehavior"]["SmoothStreaming"] == smooth

    forwarded = config["DefaultCacheBehavior"]["ForwardedValues"]
    assert forwarded["QueryString"] == qs
    assert forwarded["Cookies"]["Forward"] == "whitelist"
    assert forwarded["Cookies"]["WhitelistedNames"]["Items"] == ["x-amz-header"]


@mock_aws
def test_create_distribution_returns_etag():
    client = boto3.client("cloudfront", region_name="us-east-1")

    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert len(headers["etag"]) == 13
    assert (
        headers["location"]
        == f"https://cloudfront.amazonaws.com/2020-05-31/distribution/{dist_id}"
    )


@mock_aws
def test_create_distribution_needs_unique_caller_reference():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist1 = client.create_distribution(DistributionConfig=config)
    dist1_id = dist1["Distribution"]["Id"]

    # Try to create distribution with the same ref
    with pytest.raises(ClientError) as exc:
        client.create_distribution(DistributionConfig=config)
    err = exc.value.response["Error"]
    assert err["Code"] == "DistributionAlreadyExists"
    assert (
        err["Message"]
        == f"The caller reference that you are using to create a distribution is associated with another distribution. Already exists: {dist1_id}"
    )

    # Creating another distribution with a different reference
    config = scaffold.example_distribution_config(ref="ref2")
    dist2 = client.create_distribution(DistributionConfig=config)
    assert dist1_id != dist2["Distribution"]["Id"]

    resp = client.list_distributions()["DistributionList"]
    assert resp["Quantity"] == 2
    assert len(resp["Items"]) == 2


@mock_aws
def test_get_distribution_config_with_unknown_distribution_id():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_distribution_config(Id="unknown")

    metadata = exc.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 404
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchDistribution"
    assert err["Message"] == "The specified distribution does not exist."


@mock_aws
def test_get_distribution_config_with_mismatched_originid():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        client.create_distribution(
            DistributionConfig={
                "CallerReference": "ref",
                "Origins": {
                    "Quantity": 1,
                    "Items": [{"Id": "origin1", "DomainName": "https://getmoto.org"}],
                },
                "DefaultCacheBehavior": {
                    "TargetOriginId": "asdf",
                    "ViewerProtocolPolicy": "allow-all",
                },
                "Comment": "an optional comment that's not actually optional",
                "Enabled": False,
            }
        )
    metadata = exc.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 404
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchOrigin"
    assert (
        err["Message"] == "One or more of your origins or origin groups do not exist."
    )


@mock_aws
def test_create_distribution_with_invalid_s3_bucket():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        client.create_distribution(
            DistributionConfig={
                "CallerReference": "ref",
                "Origins": {
                    "Quantity": 1,
                    "Items": [
                        {
                            "Id": "origin1",
                            "DomainName": "https://getmoto.org",
                            "S3OriginConfig": {"OriginAccessIdentity": ""},
                        }
                    ],
                },
                "DefaultCacheBehavior": {
                    "TargetOriginId": "origin1",
                    "ViewerProtocolPolicy": "allow-all",
                },
                "Comment": "an optional comment that's not actually optional",
                "Enabled": False,
            }
        )

    metadata = exc.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 400
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgument"
    assert (
        err["Message"]
        == "The parameter Origin DomainName does not refer to a valid S3 bucket."
    )


@mock_aws
@pytest.mark.parametrize("ssl_protocols", (["TLSv1"], ["TLSv1", "SSLv3"]))
def test_create_distribution_custom_config(ssl_protocols):
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_dist_custom_config("ref", ssl_protocols)

    dist = client.create_distribution(DistributionConfig=config)["Distribution"][
        "DistributionConfig"
    ]
    assert len(dist["Origins"]["Items"]) == 1
    custom_config = dist["Origins"]["Items"][0]["CustomOriginConfig"]

    assert custom_config["HTTPPort"] == 80
    assert custom_config["HTTPSPort"] == 443
    assert custom_config["OriginReadTimeout"] == 15
    assert custom_config["OriginKeepaliveTimeout"] == 10
    assert custom_config["OriginProtocolPolicy"] == "http-only"
    assert custom_config["OriginSslProtocols"] == {
        "Items": ssl_protocols,
        "Quantity": len(ssl_protocols),
    }


@mock_aws
def test_create_distribution_minimal_custom_config():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.minimal_dist_custom_config("ref")

    dist = client.create_distribution(DistributionConfig=config)["Distribution"]
    dist_config = dist["DistributionConfig"]
    assert len(dist_config["Origins"]["Items"]) == 1
    custom_config = dist_config["Origins"]["Items"][0]["CustomOriginConfig"]

    assert custom_config["HTTPPort"] == 80
    assert custom_config["HTTPSPort"] == 443
    assert custom_config["OriginReadTimeout"] == 30
    assert custom_config["OriginKeepaliveTimeout"] == 5
    assert custom_config["OriginProtocolPolicy"] == "http-only"

    dist = client.get_distribution(Id=dist["Id"])["Distribution"]
    dist_config = dist["DistributionConfig"]
    get_custom_config = dist_config["Origins"]["Items"][0]["CustomOriginConfig"]
    assert custom_config == get_custom_config


@mock_aws
def test_list_distributions_without_any():
    client = boto3.client("cloudfront", region_name="us-east-1")

    dlist = client.list_distributions()["DistributionList"]
    assert dlist["Marker"] == ""
    assert dlist["MaxItems"] == 100
    assert dlist["IsTruncated"] is False
    assert dlist["Quantity"] == 0
    assert "Items" not in dlist


@mock_aws
def test_list_distributions():
    client = boto3.client("cloudfront", region_name="us-east-1")

    config = scaffold.example_distribution_config(ref="ref1")
    dist1 = client.create_distribution(DistributionConfig=config)["Distribution"]
    config = scaffold.example_distribution_config(ref="ref2")
    dist2 = client.create_distribution(DistributionConfig=config)["Distribution"]

    dlist = client.list_distributions()["DistributionList"]
    assert dlist["Quantity"] == 2
    assert len(dlist["Items"]) == 2

    item1 = dlist["Items"][0]
    assert item1["Id"] == dist1["Id"]
    assert "ARN" in item1
    assert item1["Status"] == "Deployed"

    item2 = dlist["Items"][1]
    assert item2["Id"] == dist2["Id"]
    assert "ARN" in item2
    assert item2["Status"] == "Deployed"


@mock_aws
def test_get_distribution():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)
    dist_id = dist["Distribution"]["Id"]

    resp = client.get_distribution(Id=dist_id)

    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert len(headers["etag"]) == 13
    dist = resp["Distribution"]
    assert dist["Id"] == dist_id
    assert dist["Status"] == "Deployed"
    assert dist["DomainName"] == dist["DomainName"]

    config = dist["DistributionConfig"]
    assert config["CallerReference"] == "ref"


@mock_aws
def test_get_unknown_distribution():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        # Should have a second param, IfMatch, that contains the ETag of the most recent GetDistribution-request
        client.get_distribution(Id="unknown")

    metadata = exc.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 404
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchDistribution"
    assert err["Message"] == "The specified distribution does not exist."


@mock_aws
def test_delete_unknown_distribution():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_distribution(Id="unknown", IfMatch="..")

    metadata = exc.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 404
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchDistribution"
    assert err["Message"] == "The specified distribution does not exist."


@mock_aws
def test_delete_distribution_without_ifmatch():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        # Should have a second param, IfMatch, that contains the ETag of the most recent GetDistribution-request
        client.delete_distribution(Id="...")

    metadata = exc.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 400
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidIfMatchVersion"
    assert (
        err["Message"]
        == "The If-Match version is missing or not valid for the resource."
    )


@mock_aws
def test_delete_distribution_random_etag():
    """
    Etag validation is not implemented yet
    Calling the delete-method with any etag will pass
    """
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist1 = client.create_distribution(DistributionConfig=config)
    dist_id = dist1["Distribution"]["Id"]

    client.delete_distribution(Id=dist_id, IfMatch="anything")

    with pytest.raises(ClientError) as exc:
        client.get_distribution(Id=dist_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchDistribution"


@mock_aws
def test_get_distribution_config():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)
    dist_id = dist["Distribution"]["Id"]

    config = client.get_distribution_config(Id=dist_id)["DistributionConfig"]
    assert config["CallerReference"] == "ref"

    assert config["Aliases"]["Quantity"] == 0

    origins = config["Origins"]
    assert origins["Quantity"] == 1
    assert len(origins["Items"]) == 1
    origin = origins["Items"][0]
    assert origin["Id"] == "origin1"
    assert origin["DomainName"] == "asdf.s3.us-east-1.amazonaws.com"
    assert origin["OriginPath"] == "/example"

    assert origin["CustomHeaders"]["Quantity"] == 0

    assert origin["ConnectionAttempts"] == 3
    assert origin["ConnectionTimeout"] == 10
    assert origin["OriginShield"] == {"Enabled": False}

    assert config["OriginGroups"] == {"Quantity": 0}

    default_cache = config["DefaultCacheBehavior"]
    assert default_cache["TargetOriginId"] == "origin1"

    signers = default_cache["TrustedSigners"]
    assert signers["Enabled"] is False
    assert signers["Quantity"] == 0

    groups = default_cache["TrustedKeyGroups"]
    assert groups["Enabled"] is False
    assert groups["Quantity"] == 0

    assert default_cache["ViewerProtocolPolicy"] == "allow-all"

    methods = default_cache["AllowedMethods"]
    assert methods["Quantity"] == 2
    assert set(methods["Items"]) == {"HEAD", "GET"}

    cached_methods = methods["CachedMethods"]
    assert cached_methods["Quantity"] == 2
    assert set(cached_methods["Items"]) == {"HEAD", "GET"}

    assert default_cache["SmoothStreaming"] is False
    assert default_cache["Compress"] is True
    assert default_cache["LambdaFunctionAssociations"] == {"Quantity": 0}
    assert default_cache["FunctionAssociations"] == {"Quantity": 0}
    assert default_cache["FieldLevelEncryptionId"] == ""
    assert "CachePolicyId" in default_cache

    assert config["CacheBehaviors"] == {"Quantity": 0}
    assert config["CustomErrorResponses"] == {"Quantity": 0}
    assert config["Comment"] == "an optional comment that's not actually optional"

    logging = config["Logging"]
    assert logging["Enabled"] is False
    assert logging["IncludeCookies"] is False
    assert logging["Bucket"] == ""
    assert logging["Prefix"] == ""

    assert config["PriceClass"] == "PriceClass_All"
    assert config["Enabled"] is False
    assert "WebACLId" in config
    assert config["HttpVersion"] == "http2"
    assert config["IsIPV6Enabled"] is True

    cert = config["ViewerCertificate"]
    assert cert["CloudFrontDefaultCertificate"] is True
    assert cert["MinimumProtocolVersion"] == "TLSv1"
    assert cert["CertificateSource"] == "cloudfront"

    assert config["Restrictions"]["GeoRestriction"] == {
        "RestrictionType": "none",
        "Quantity": 0,
    }

    assert config["WebACLId"] == ""


@mock_aws
def test_add_new_gateway_basic():
    # Setup
    cloudfront_client_mock = boto3.client("cloudfront", region_name="us-east-1")
    config = scaffold.example_distribution_config("ref")
    distribution_id = cloudfront_client_mock.create_distribution(
        DistributionConfig=config
    )["Distribution"]["Id"]
    existing_config = cloudfront_client_mock.get_distribution(Id=distribution_id)[
        "Distribution"
    ]["DistributionConfig"]
    new_behaviors = [
        {
            "PathPattern": "bla/*",
            "TargetOriginId": "test.invalid",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 7,
                "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            "SmoothStreaming": False,
            "Compress": False,
            "LambdaFunctionAssociations": {"Quantity": 0},
            "FieldLevelEncryptionId": "",
            "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # CachingDisabled
            "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",  # AllViewerExceptHostHeader
        }
    ]

    new_config = existing_config
    new_config["CacheBehaviors"]["Quantity"] = 1
    new_config["CacheBehaviors"]["Items"] = new_behaviors

    # Execute
    cloudfront_client_mock.update_distribution(
        DistributionConfig=new_config, Id=distribution_id, IfMatch="1"
    )
    result = cloudfront_client_mock.get_distribution(Id=distribution_id)[
        "Distribution"
    ]["DistributionConfig"]

    # Verify
    assert result["CacheBehaviors"]["Quantity"] == 1
    assert (
        result["CacheBehaviors"]["Items"][0]["PathPattern"]
        == new_behaviors[0]["PathPattern"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["TargetOriginId"]
        == new_behaviors[0]["TargetOriginId"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["ViewerProtocolPolicy"]
        == new_behaviors[0]["ViewerProtocolPolicy"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["AllowedMethods"]
        == new_behaviors[0]["AllowedMethods"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["SmoothStreaming"]
        == new_behaviors[0]["SmoothStreaming"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["Compress"] == new_behaviors[0]["Compress"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["LambdaFunctionAssociations"]["Quantity"]
        == new_behaviors[0]["LambdaFunctionAssociations"]["Quantity"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["FieldLevelEncryptionId"]
        == new_behaviors[0]["FieldLevelEncryptionId"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["CachePolicyId"]
        == new_behaviors[0]["CachePolicyId"]
    )
    assert (
        result["CacheBehaviors"]["Items"][0]["OriginRequestPolicyId"]
        == new_behaviors[0]["OriginRequestPolicyId"]
    )
