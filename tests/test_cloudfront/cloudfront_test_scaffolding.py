# Example distribution config used in tests in both test_cloudfront.py
# as well as test_cloudfront_distributions.py.


def example_distribution_config(ref):
    """Return a basic example distribution config for use in tests."""
    return {
        "CallerReference": ref,
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "origin1",
                    "DomainName": "asdf.s3.us-east-1.amazonaws.com",
                    "OriginPath": "/example",
                    "S3OriginConfig": {
                        "OriginAccessIdentity": "origin-access-identity/cloudfront/00000000000001"
                    },
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "origin1",
            "ViewerProtocolPolicy": "allow-all",
            "MinTTL": 10,
            "ForwardedValues": {"QueryString": False, "Cookies": {"Forward": "none"}},
        },
        "Comment": "an optional comment that's not actually optional",
        "Enabled": False,
    }


def example_dist_config_with_tags(ref):
    config = example_distribution_config(ref)
    config["Tags"] = {
        "Items": [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]
    }
    return config


def example_dist_custom_config(ref):
    return {
        "CallerReference": ref,
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "origin1",
                    "DomainName": "asdf.s3.us-east-1.amazonaws.com",
                    "CustomOriginConfig": {
                        "HTTPPort": 80,
                        "HTTPSPort": 443,
                        "OriginKeepaliveTimeout": 10,
                        "OriginProtocolPolicy": "http-only",
                        "OriginReadTimeout": 15,
                        "OriginSslProtocols": {
                            "Quantity": 2,
                            "Items": ["TLSv1", "SSLv3"],
                        },
                    },
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "origin1",
            "ViewerProtocolPolicy": "allow-all",
            "MinTTL": 10,
            "ForwardedValues": {"QueryString": False, "Cookies": {"Forward": "none"}},
        },
        "Comment": "an optional comment that's not actually optional",
        "Enabled": False,
    }


def minimal_dist_custom_config(ref: str):
    return {
        "CallerReference": ref,
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "my-origin",
                    "DomainName": "example.com",
                    "CustomOriginConfig": {
                        "HTTPPort": 80,
                        "HTTPSPort": 443,
                        "OriginProtocolPolicy": "http-only",
                    },
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "my-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "DefaultTTL": 86400,
            "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
                "Headers": {"Quantity": 0},
            },
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "MinTTL": 0,
        },
        "Comment": "My CloudFront distribution",
        "Enabled": True,
    }
