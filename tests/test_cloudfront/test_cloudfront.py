"""Unit tests for cloudfront-supported APIs."""
import pytest
import boto3
from botocore.exceptions import ClientError, ParamValidationError
from moto import mock_cloudfront
import sure  # noqa # pylint: disable=unused-import
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from . import cloudfront_test_scaffolding as scaffold

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_cloudfront
def test_update_distribution():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)
    dist_id = dist["Distribution"]["Id"]
    dist_etag = dist["ETag"]

    dist_config = dist["Distribution"]["DistributionConfig"]
    aliases = ["alias1", "alias2"]
    dist_config["Origins"]["Items"][0]["OriginPath"] = "/updated"
    dist_config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}

    resp = client.update_distribution(
        DistributionConfig=dist_config, Id=dist_id, IfMatch=dist_etag
    )

    resp.should.have.key("Distribution")
    distribution = resp["Distribution"]
    distribution.should.have.key("Id")
    distribution.should.have.key("ARN").equals(
        f"arn:aws:cloudfront:{ACCOUNT_ID}:distribution/{distribution['Id']}"
    )
    distribution.should.have.key("Status").equals("Deployed")
    distribution.should.have.key("LastModifiedTime")
    distribution.should.have.key("InProgressInvalidationBatches").equals(0)
    distribution.should.have.key("DomainName").should.contain(".cloudfront.net")

    distribution.should.have.key("ActiveTrustedSigners")
    signers = distribution["ActiveTrustedSigners"]
    signers.should.have.key("Enabled").equals(False)
    signers.should.have.key("Quantity").equals(0)

    distribution.should.have.key("ActiveTrustedKeyGroups")
    key_groups = distribution["ActiveTrustedKeyGroups"]
    key_groups.should.have.key("Enabled").equals(False)
    key_groups.should.have.key("Quantity").equals(0)

    distribution.should.have.key("DistributionConfig")
    config = distribution["DistributionConfig"]
    config.should.have.key("CallerReference").should.equal("ref")

    config.should.have.key("Aliases")
    config["Aliases"].should.equal(dist_config["Aliases"])

    config.should.have.key("Origins")
    origins = config["Origins"]
    origins.should.have.key("Quantity").equals(1)
    origins.should.have.key("Items").length_of(1)
    origin = origins["Items"][0]
    origin.should.have.key("Id").equals("origin1")
    origin.should.have.key("DomainName").equals("asdf.s3.us-east-1.amazonaws.com")
    origin.should.have.key("OriginPath").equals("/updated")

    origin.should.have.key("CustomHeaders")
    origin["CustomHeaders"].should.have.key("Quantity").equals(0)

    origin.should.have.key("ConnectionAttempts").equals(3)
    origin.should.have.key("ConnectionTimeout").equals(10)
    origin.should.have.key("OriginShield").equals(
        {"Enabled": False, "OriginShieldRegion": "None"}
    )

    config.should.have.key("OriginGroups").equals({"Quantity": 0})

    config.should.have.key("DefaultCacheBehavior")
    default_cache = config["DefaultCacheBehavior"]
    default_cache.should.have.key("TargetOriginId").should.equal("origin1")
    default_cache.should.have.key("TrustedSigners")

    signers = default_cache["TrustedSigners"]
    signers.should.have.key("Enabled").equals(False)
    signers.should.have.key("Quantity").equals(0)

    default_cache.should.have.key("TrustedKeyGroups")
    groups = default_cache["TrustedKeyGroups"]
    groups.should.have.key("Enabled").equals(False)
    groups.should.have.key("Quantity").equals(0)

    default_cache.should.have.key("ViewerProtocolPolicy").equals("allow-all")

    default_cache.should.have.key("AllowedMethods")
    methods = default_cache["AllowedMethods"]
    methods.should.have.key("Quantity").equals(2)
    methods.should.have.key("Items")
    set(methods["Items"]).should.equal({"HEAD", "GET"})

    methods.should.have.key("CachedMethods")
    cached_methods = methods["CachedMethods"]
    cached_methods.should.have.key("Quantity").equals(2)
    set(cached_methods["Items"]).should.equal({"HEAD", "GET"})

    default_cache.should.have.key("SmoothStreaming").equals(False)
    default_cache.should.have.key("Compress").equals(True)
    default_cache.should.have.key("LambdaFunctionAssociations").equals({"Quantity": 0})
    default_cache.should.have.key("FunctionAssociations").equals({"Quantity": 0})
    default_cache.should.have.key("FieldLevelEncryptionId").equals("")
    default_cache.should.have.key("CachePolicyId")

    config.should.have.key("CacheBehaviors").equals({"Quantity": 0})
    config.should.have.key("CustomErrorResponses").equals({"Quantity": 0})
    config.should.have.key("Comment").equals(
        "an optional comment that's not actually optional"
    )

    config.should.have.key("Logging")
    logging = config["Logging"]
    logging.should.have.key("Enabled").equals(False)
    logging.should.have.key("IncludeCookies").equals(False)
    logging.should.have.key("Bucket").equals("")
    logging.should.have.key("Prefix").equals("")

    config.should.have.key("PriceClass").equals("PriceClass_All")
    config.should.have.key("Enabled").equals(False)
    config.should.have.key("WebACLId")
    config.should.have.key("HttpVersion").equals("http2")
    config.should.have.key("IsIPV6Enabled").equals(True)

    config.should.have.key("ViewerCertificate")
    cert = config["ViewerCertificate"]
    cert.should.have.key("CloudFrontDefaultCertificate").equals(True)
    cert.should.have.key("MinimumProtocolVersion").equals("TLSv1")
    cert.should.have.key("CertificateSource").equals("cloudfront")

    config.should.have.key("Restrictions")
    config["Restrictions"].should.have.key("GeoRestriction")
    restriction = config["Restrictions"]["GeoRestriction"]
    restriction.should.have.key("RestrictionType").equals("none")
    restriction.should.have.key("Quantity").equals(0)


@mock_cloudfront
def test_update_distribution_no_such_distId():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)

    # Make up a fake dist ID by reversing the actual ID
    dist_id = dist["Distribution"]["Id"][::-1]
    dist_etag = dist["ETag"]

    dist_config = dist["Distribution"]["DistributionConfig"]
    aliases = ["alias1", "alias2"]
    dist_config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}

    with pytest.raises(ClientError) as error:
        client.update_distribution(
            DistributionConfig=dist_config, Id=dist_id, IfMatch=dist_etag
        )

    metadata = error.value.response["ResponseMetadata"]
    metadata["HTTPStatusCode"].should.equal(404)
    err = error.value.response["Error"]
    err["Code"].should.equal("NoSuchDistribution")
    err["Message"].should.equal("The specified distribution does not exist.")


@mock_cloudfront
def test_update_distribution_distId_is_None():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)

    # Make up a fake dist ID by reversing the actual ID
    dist_id = None
    dist_etag = dist["ETag"]

    dist_config = dist["Distribution"]["DistributionConfig"]
    aliases = ["alias1", "alias2"]
    dist_config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}

    with pytest.raises(ParamValidationError) as error:
        client.update_distribution(
            DistributionConfig=dist_config, Id=dist_id, IfMatch=dist_etag
        )

    typename = error.typename
    typename.should.equal("ParamValidationError")
    error_str = "botocore.exceptions.ParamValidationError: Parameter validation failed:\nInvalid type for parameter Id, value: None, type: <class 'NoneType'>, valid types: <class 'str'>"
    error.exconly().should.equal(error_str)


@mock_cloudfront
def test_update_distribution_IfMatch_not_set():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)

    # Make up a fake dist ID by reversing the actual ID
    dist_id = dist["Distribution"]["Id"]

    dist_config = dist["Distribution"]["DistributionConfig"]
    aliases = ["alias1", "alias2"]
    dist_config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}

    with pytest.raises(ClientError) as error:
        client.update_distribution(
            DistributionConfig=dist_config, Id=dist_id, IfMatch=""
        )

    metadata = error.value.response["ResponseMetadata"]
    metadata["HTTPStatusCode"].should.equal(400)
    err = error.value.response["Error"]
    err["Code"].should.equal("InvalidIfMatchVersion")
    msg = "The If-Match version is missing or not valid for the resource."
    err["Message"].should.equal(msg)


@mock_cloudfront
def test_update_distribution_dist_config_not_set():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)

    # Make up a fake dist ID by reversing the actual ID
    dist_id = dist["Distribution"]["Id"]
    dist_etag = dist["ETag"]

    with pytest.raises(ParamValidationError) as error:
        client.update_distribution(Id=dist_id, IfMatch=dist_etag)

    typename = error.typename
    typename.should.equal("ParamValidationError")
    error_str = 'botocore.exceptions.ParamValidationError: Parameter validation failed:\nMissing required parameter in input: "DistributionConfig"'
    error.exconly().should.equal(error_str)
