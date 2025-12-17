import time

import boto3
import json
import time
import os
import subprocess
from datetime import timezone
from moto.core.utils import unix_time
from moto.ec2.utils import gen_moto_amis


def retrieve_by_path(client, path):
    x = client.get_parameters_by_path(Path=path, Recursive=True)
    parameters = x["Parameters"]
    next_token = x["NextToken"]
    while next_token:
        x = client.get_parameters_by_path(
            Path=path, Recursive=True, NextToken=next_token
        )
        parameters.extend(x["Parameters"])
        next_token = x.get("NextToken")

    return parameters


def main():
    """
    Retrieve the latest AMI-details from SSM
     - Download from AWS
     - Store this in the dedicated moto/ssm/resources-folder
    """

    regions = boto3.Session().get_available_regions("ssm")
    # Malaysia is a new region, and not yet exposed by get_available_regions
    regions.append("ap-southeast-5")

    for region in regions:
        client = boto3.client("ssm", region_name=region)
        ec2 = boto3.client("ec2", region_name=region)

        default_param_path = "/aws/service/ami-amazon-linux-latest"

        # Retrieve default AMI values
        try:
            params = retrieve_by_path(client, default_param_path)
            for param in params:
                param["LastModifiedDate"] = unix_time(
                    param["LastModifiedDate"]
                    .astimezone(timezone.utc)
                    .replace(tzinfo=None)
                )

            root_dir = (
                subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
                .decode()
                .strip()
            )
            dest = os.path.join(
                root_dir, f"moto/ssm/resources/ami-amazon-linux-latest/{region}.json"
            )
            print("Writing data to {0}".format(dest))
            with open(dest, "w") as open_file:
                json.dump(params, open_file, sort_keys=True, indent=2)

            # Retrieve details about AMIs from EC2
            image_ids = [p["Value"] for p in params]
            images = ec2.describe_images(ImageIds=image_ids)["Images"]
            image_as_dicts = gen_moto_amis(images)
            dest = os.path.join(
                root_dir, f"moto/ec2/resources/latest_amis/{region}.json"
            )
            print("Writing data to {0}".format(dest))
            with open(dest, "w") as open_file:
                json.dump(image_as_dicts, open_file, sort_keys=True, indent=2)

            time.sleep(0.5)
        except Exception as e:
            print(e)
            # We might encounter an error if we do not have access to a region - just ignore and try the next region


if __name__ == "__main__":
    main()
