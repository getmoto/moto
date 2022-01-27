#!/usr/bin/env python

import json
import os
import subprocess

from time import sleep

import boto3
from boto3 import Session


def main():
    print("Getting InstanceTypes from all regions")
    regions = []
    regions.extend(Session().get_available_regions("ec2"))
    regions.extend(Session().get_available_regions("ec2", partition_name="aws-us-gov"))
    regions.extend(Session().get_available_regions("ec2", partition_name="aws-cn"))
    print("Found " + str(len(regions)) + " regions")

    instances = []
    for region in regions:
        try:
            ec2 = boto3.client("ec2", region_name=region)
            offerings = ec2.describe_instance_types()
            instances.extend(offerings["InstanceTypes"])
            next_token = offerings.get("NextToken", "")
            while next_token:
                offerings = ec2.describe_instance_types(NextToken=next_token)
                instances.extend(offerings["InstanceTypes"])
                next_token = offerings.get("NextToken", None)
        except Exception:
            print("Could not fetch instance types from region:", region)
        # We don't want it to look like we're DDOS'ing AWS
        sleep(1)

    print("Parsing data")
    result = {}
    for instance in instances:
        result[instance.get("InstanceType")] = instance

    root_dir = (
        subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
        .decode()
        .strip()
    )
    dest = os.path.join(root_dir, "moto/ec2/resources/instance_types.json")
    print("Writing data to {0}".format(dest))
    with open(dest, "w") as open_file:
        json.dump(result, open_file, sort_keys=True, indent=1)


if __name__ == "__main__":
    main()
