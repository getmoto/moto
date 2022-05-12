import boto3
from botocore.exceptions import ClientError
from moto import mock_cloudfront
from moto.core import ACCOUNT_ID
from . import cloudfront_test_scaffolding as scaffold
import pytest
import sure  # noqa # pylint: disable=unused-import


@mock_cloudfront
def test_create_distribution_s3_minimum():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")

    resp = client.create_distribution(DistributionConfig=config)
    resp.should.have.key("Distribution")

    distribution = resp["Distribution"]
    distribution.should.have.key("Id")
    distribution.should.have.key("ARN").equals(
        f"arn:aws:cloudfront:{ACCOUNT_ID}:distribution/{distribution['Id']}"
    )
    distribution.should.have.key("Status").equals("InProgress")
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
    config["Aliases"].should.have.key("Quantity").equals(0)

    config.should.have.key("Origins")
    origins = config["Origins"]
    origins.should.have.key("Quantity").equals(1)
    origins.should.have.key("Items").length_of(1)
    origin = origins["Items"][0]
    origin.should.have.key("Id").equals("origin1")
    origin.should.have.key("DomainName").equals("asdf.s3.us-east-1.amazonaws.com")
    origin.should.have.key("OriginPath").equals("")

    origin.should.have.key("CustomHeaders")
    origin["CustomHeaders"].should.have.key("Quantity").equals(0)

    origin.should.have.key("ConnectionAttempts").equals(3)
    origin.should.have.key("ConnectionTimeout").equals(10)
    origin.should.have.key("OriginShield").equals({"Enabled": False})

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
def test_create_distribution_with_additional_fields():
    client = boto3.client("cloudfront", region_name="us-west-1")

    config = scaffold.example_distribution_config("ref")
    config["Aliases"] = {"Quantity": 2, "Items": ["alias1", "alias2"]}
    resp = client.create_distribution(DistributionConfig=config)
    distribution = resp["Distribution"]
    distribution.should.have.key("DistributionConfig")
    config = distribution["DistributionConfig"]
    config.should.have.key("Aliases").equals(
        {"Items": ["alias1", "alias2"], "Quantity": 2}
    )


@mock_cloudfront
def test_create_distribution_returns_etag():
    client = boto3.client("cloudfront", region_name="us-east-1")

    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    headers.should.have.key("etag").length_of(13)
    headers.should.have.key("location").equals(
        f"https://cloudfront.amazonaws.com/2020-05-31/distribution/{dist_id}"
    )


@mock_cloudfront
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
    err["Code"].should.equal("DistributionAlreadyExists")
    err["Message"].should.equal(
        f"The caller reference that you are using to create a distribution is associated with another distribution. Already exists: {dist1_id}"
    )

    # Creating another distribution with a different reference
    config = scaffold.example_distribution_config(ref="ref2")
    dist2 = client.create_distribution(DistributionConfig=config)
    dist1_id.shouldnt.equal(dist2["Distribution"]["Id"])

    # TODO: Verify two exist, using the list_distributions method


@mock_cloudfront
def test_create_distribution_with_mismatched_originid():
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
    metadata["HTTPStatusCode"].should.equal(404)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchOrigin")
    err["Message"].should.equal(
        "One or more of your origins or origin groups do not exist."
    )


@mock_cloudfront
def test_create_origin_without_origin_config():
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
                    "TargetOriginId": "origin1",
                    "ViewerProtocolPolicy": "allow-all",
                },
                "Comment": "an optional comment that's not actually optional",
                "Enabled": False,
            }
        )

    metadata = exc.value.response["ResponseMetadata"]
    metadata["HTTPStatusCode"].should.equal(400)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidOrigin")
    err["Message"].should.equal(
        "The specified origin server does not exist or is not valid."
    )


@mock_cloudfront
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
    metadata["HTTPStatusCode"].should.equal(400)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidArgument")
    err["Message"].should.equal(
        "The parameter Origin DomainName does not refer to a valid S3 bucket."
    )


@mock_cloudfront
def test_list_distributions_without_any():
    client = boto3.client("cloudfront", region_name="us-east-1")

    resp = client.list_distributions()
    resp.should.have.key("DistributionList")
    dlist = resp["DistributionList"]
    dlist.should.have.key("Marker").equals("")
    dlist.should.have.key("MaxItems").equals(100)
    dlist.should.have.key("IsTruncated").equals(False)
    dlist.should.have.key("Quantity").equals(0)
    dlist.shouldnt.have.key("Items")


@mock_cloudfront
def test_list_distributions():
    client = boto3.client("cloudfront", region_name="us-east-1")

    config = scaffold.example_distribution_config(ref="ref1")
    dist1 = client.create_distribution(DistributionConfig=config)["Distribution"]
    config = scaffold.example_distribution_config(ref="ref2")
    dist2 = client.create_distribution(DistributionConfig=config)["Distribution"]

    resp = client.list_distributions()
    resp.should.have.key("DistributionList")
    dlist = resp["DistributionList"]
    dlist.should.have.key("Quantity").equals(2)
    dlist.should.have.key("Items").length_of(2)

    item1 = dlist["Items"][0]
    item1.should.have.key("Id").equals(dist1["Id"])
    item1.should.have.key("ARN")
    item1.should.have.key("Status").equals("Deployed")

    item2 = dlist["Items"][1]
    item2.should.have.key("Id").equals(dist2["Id"])
    item2.should.have.key("ARN")
    item2.should.have.key("Status").equals("Deployed")


@mock_cloudfront
def test_get_distribution():
    client = boto3.client("cloudfront", region_name="us-east-1")

    # Create standard distribution
    config = scaffold.example_distribution_config(ref="ref")
    dist = client.create_distribution(DistributionConfig=config)
    dist_id = dist["Distribution"]["Id"]

    resp = client.get_distribution(Id=dist_id)

    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    headers.should.have.key("etag").length_of(13)
    dist = resp["Distribution"]
    dist.should.have.key("Id").equals(dist_id)
    dist.should.have.key("Status").equals("Deployed")
    dist.should.have.key("DomainName").equals(dist["DomainName"])

    dist.should.have.key("DistributionConfig")
    config = dist["DistributionConfig"]
    config.should.have.key("CallerReference").should.equal("ref")


@mock_cloudfront
def test_get_unknown_distribution():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        # Should have a second param, IfMatch, that contains the ETag of the most recent GetDistribution-request
        client.get_distribution(Id="unknown")

    metadata = exc.value.response["ResponseMetadata"]
    metadata["HTTPStatusCode"].should.equal(404)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchDistribution")
    err["Message"].should.equal("The specified distribution does not exist.")


@mock_cloudfront
def test_delete_unknown_distribution():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_distribution(Id="unknown", IfMatch="..")

    metadata = exc.value.response["ResponseMetadata"]
    metadata["HTTPStatusCode"].should.equal(404)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchDistribution")
    err["Message"].should.equal("The specified distribution does not exist.")


@mock_cloudfront
def test_delete_distribution_without_ifmatch():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as exc:
        # Should have a second param, IfMatch, that contains the ETag of the most recent GetDistribution-request
        client.delete_distribution(Id="...")

    metadata = exc.value.response["ResponseMetadata"]
    metadata["HTTPStatusCode"].should.equal(400)
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidIfMatchVersion")
    err["Message"].should.equal(
        "The If-Match version is missing or not valid for the resource."
    )


@mock_cloudfront
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
    err["Code"].should.equal("NoSuchDistribution")
