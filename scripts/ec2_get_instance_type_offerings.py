#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Get InstanceTypeOfferings from AWS
Stores result in moto/ec2/resources/instance_type_offerings/{location_type}/{region}.json
Where {location_type} is one of region/availability-zone/availability-zone-id

Note that you will get the following error if a region is not available to you:
  An error occurred (AuthFailure) when calling the DescribeInstanceTypeOfferings operation:
  AWS was not able to validate the provided access credentials
"""

import json
import os
import subprocess
from time import sleep

import boto3
from boto3 import Session

PATH = "moto/ec2/resources/instance_type_offerings"
TYPES = ["region", "availability-zone", "availability-zone-id"]


def main():
    print("Getting InstanceTypeOfferings from all regions")
    regions = []
    regions.extend(Session().get_available_regions("ec2"))
    regions.extend(Session().get_available_regions("ec2", partition_name="aws-us-gov"))
    regions.extend(Session().get_available_regions("ec2", partition_name="aws-cn"))
    # Malaysia is a new region, and not yet exposed by get_available_regions
    regions.append("ap-southeast-5")
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
                for i in instances:
                    del i[
                        "LocationType"
                    ]  # This can be reproduced, no need to persist it
                instances = sorted(
                    instances, key=lambda i: (i["Location"], i["InstanceType"])
                )

                # Ensure we use the correct US-west availability zones
                # There are three, but accounts only have access to two
                # Because of this, some accounts have access to (us-west-1a or us-west-1b) and us-west-1c
                # As our EC2-module assumes us-west-1a and us-west-1b, we have to rename the zones accordingly
                # https://github.com/getmoto/moto/issues/5494
                if region == "us-west-1" and location_type == "availability-zone":
                    zones = set([i["Location"] for i in instances])
                    # If AWS returns b and c, we have to convert b --> a
                    if zones == {"us-west-1b", "us-west-1c"}:
                        for i in instances:
                            if i["Location"] == "us-west-1b":
                                i["Location"] = "us-west-1a"
                    # If AWS returns c, we always have to convert c --> b (the other location will always be a at this point)
                    if "us-west-1c" in zones:
                        for i in instances:
                            if i["Location"] == "us-west-1c":
                                i["Location"] = "us-west-1b"

                print("Writing data to {0}".format(dest))
                with open(dest, "w+") as open_file:
                    json.dump(instances, open_file, indent=1)
            except Exception as e:
                print("Unable to write data to {0}".format(dest))
                print(e)
        # We don't want it to look like we're DDOS'ing AWS
        sleep(1)


if __name__ == "__main__":
    main()
