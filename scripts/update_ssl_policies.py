#!/bin/bash
import json

import boto3
import re

CAMEL_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")

KEY_BLACKLIST = ["SupportedLoadBalancerTypes"]


def camel_case_to_snake_case(name: str):
    return CAMEL_CASE_PATTERN.sub("_", name).lower()


def get_ssl_elb_ssl_policies():
    elbv2_client = boto3.client("elbv2")
    return elbv2_client.describe_ssl_policies()["SslPolicies"]


def transform_policies(ssl_policies: dict):
    if isinstance(ssl_policies, list):
        return [transform_policies(item) for item in ssl_policies]
    if not isinstance(ssl_policies, dict):
        return ssl_policies
    result = {}
    for key, value in sorted(ssl_policies.items()):
        if key in KEY_BLACKLIST:
            continue
        new_key = camel_case_to_snake_case(key)
        result[new_key] = transform_policies(value)
    return result


def main():
    policies = get_ssl_elb_ssl_policies()
    transformed_policies = transform_policies(policies)
    print(json.dumps(transformed_policies, indent=4))


if __name__ == "__main__":
    main()
