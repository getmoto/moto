#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Get InstanceTypeOfferings from AWS
Stores result in moto/ec2/resources/instance_type_offerings/{location_type}/{region}.json
Where {location_type} is one of region/availability-zone/availability-zone-id

Note that you will get the following error if a region is not available to you:
  An error occurred (AuthFailure) when calling the DescribeInstanceTypeOfferings operation:
  AWS was not able to validate the provided access credentials
"""

import boto3
import json
import os
import subprocess
from boto3 import Session
from time import sleep

PATH = "moto/ec2/resources/instance_type_offerings"
TYPES = ["region", "availability-zone", "availability-zone-id"]


def main():
    print("Getting InstanceTypeOfferings from all regions")
    regions = []
    regions.extend(Session().get_available_regions("ec2"))
    regions.extend(Session().get_available_regions("ec2", partition_name="aws-us-gov"))
    regions.extend(Session().get_available_regions("ec2", partition_name="aws-cn"))
    print("Found " + str(len(regions)) + " regions")

    root_dir = (
        subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
        .decode()
        .strip()
    )
    for region in regions:
        for location_type in TYPES:
            ec2 = boto3.client("ec2", region_name=region)
            dest = os.path.join(
                root_dir, "{0}/{1}/{2}.json".format(PATH, location_type, region)
            )
            try:
                instances = []
                offerings = ec2.describe_instance_type_offerings(
                    LocationType=location_type
                )
                instances.extend(offerings["InstanceTypeOfferings"])
                next_token = offerings.get("NextToken", "")
                while next_token:
                    offerings = ec2.describe_instance_type_offerings(
                        LocationType=location_type, NextToken=next_token
                    )
                    instances.extend(offerings["InstanceTypeOfferings"])
                    next_token = offerings.get("NextToken", None)
                print("Writing data to {0}".format(dest))
                with open(dest, "w+") as open_file:
                    json.dump(instances, open_file, sort_keys=True)
            except Exception as e:
                print("Unable to write data to {0}".format(dest))
                print(e)
        # We don't want it to look like we're DDOS'ing AWS
        sleep(1)


if __name__ == "__main__":
    main()
