"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_cloudfront import CloudFrontClient, CloudFrontConfig
    from aws_sdk_cloudfront.models import NoSuchDistribution
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-cloudfront is not installed", allow_module_level=True)


@mock_aws
def test_static_website_distribution():
    """Serve a static website from S3, invalidate the cache after a deploy, then tear it down."""
    config = CloudFrontConfig.resolve(region="us-east-1")
    origin_domain = f"website-{uuid4()}.s3.us-east-1.amazonaws.com"

    with CloudFrontClient(config=config) as client:
        created = client.create_distribution_with_tags(
            distribution_config_with_tags={
                "distribution_config": {
                    "caller_reference": str(uuid4()),
                    "comment": "Marketing website",
                    "enabled": True,
                    "default_root_object": "index.html",
                    "origins": {
                        "quantity": 1,
                        "items": [
                            {
                                "id": "website-bucket",
                                "domain_name": origin_domain,
                                "s3_origin_config": {"origin_access_identity": ""},
                            }
                        ],
                    },
                    "default_cache_behavior": {
                        "target_origin_id": "website-bucket",
                        "viewer_protocol_policy": "redirect-to-https",
                        "min_ttl": 0,
                    },
                },
                "tags": {"items": [{"key": "team", "value": "marketing"}]},
            }
        )
        distribution = created.distribution
        assert distribution.domain_name.endswith(".cloudfront.net")
        assert distribution.distribution_config.default_root_object == "index.html"
        assert distribution.distribution_config.origins.items[0].domain_name == (
            origin_domain
        )

        tags = client.list_tags_for_resource(resource=distribution.arn).tags
        assert [(t.key, t.value) for t in tags.items] == [("team", "marketing")]

        # Invalidate the cache after deploying a new version of the website
        invalidation = client.create_invalidation(
            distribution_id=distribution.id,
            invalidation_batch={
                "paths": {"quantity": 2, "items": ["/index.html", "/css/*"]},
                "caller_reference": str(uuid4()),
            },
        ).invalidation
        fetched = client.get_invalidation(
            distribution_id=distribution.id, id=invalidation.id
        ).invalidation
        assert fetched.invalidation_batch.paths.items == ["/index.html", "/css/*"]

        # A distribution has to be disabled before it can be deleted
        current = client.get_distribution_config(id=distribution.id)
        current.distribution_config.enabled = False
        updated = client.update_distribution(
            id=distribution.id,
            distribution_config=current.distribution_config,
            if_match=current.e_tag,
        )
        assert updated.distribution.distribution_config.enabled is False

        client.delete_distribution(id=distribution.id, if_match=updated.e_tag)
        with pytest.raises(NoSuchDistribution):
            client.get_distribution(id=distribution.id)
