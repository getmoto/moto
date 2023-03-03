import time
import json
from datetime import timezone
from pathlib import Path

import boto3
import botocore

from moto.core.utils import unix_time
from moto.ec2.utils import gen_moto_amis
from moto.ssm.utils import convert_to_tree

session = boto3.Session()


def retrieve_by_path(client, path):
    print("Attempting to retrieve data for path={}", path)
    response = client.get_parameters_by_path(Path=path, Recursive=True)
    parameters = response["Parameters"]
    next_token = response["NextToken"]
    while next_token:
        response = client.get_parameters_by_path(Path=path, Recursive=True, NextToken=next_token)
        parameters.extend(response["Parameters"])
        next_token = response.get("NextToken")

    return parameters

def save_to_file(destination_path: str, params: dict):
    print("Attempting to save data to {}", destination_path)
    file_path = Path(Path.cwd(), destination_path)
    file_path.parent.mkdir(exist_ok=True, parents=True)

    with file_path.open("w") as fb:
        json.dump(params, fb, sort_keys=True, indent=2)


def retrieve_ec2_data(image_ids: list, region: str):
    ec2_client = session.client("ec2", region_name=region)

    images = ec2_client.describe_images(ImageIds=image_ids)["Images"]

    return gen_moto_amis(images)


def main():
    """
    Retrieve the latest AMI-details from SSM
     - Download from AWS
     - Store this in the dedicated moto/ssm/resources-folder
    """
    for region in session.get_available_regions("ssm"):
        ssm_client = session.client('ssm', region_name=region)

        default_param_path = "/aws/service/ecs/optimized-ami"

        # Retrieve default AMI values
        try:
            print("Retrieving data for {}" , region)

            parameters = retrieve_by_path(ssm_client, default_param_path)

            if not parameters:
                continue

            image_ids = []

            for param in parameters:
                param["LastModifiedDate"] = unix_time(param["LastModifiedDate"].astimezone(timezone.utc).replace(tzinfo=None))

                if isinstance(param["Value"], str) and param["Value"][0] == "{":
                    param["Value"] = json.loads(param["Value"])
                    image_ids.append(param["Value"]["image_id"])

                # We can recreate these params
                param.pop("DataType", None)
                param.pop("Type", None)
                param.pop("ARN", None)

            image_ids = list(set(image_ids))

            tree = convert_to_tree(parameters)

            destination_path = f"moto/ssm/resources/ecs/optimized_amis/{region}.json"
            save_to_file(destination_path, tree)

            # Retrieve details about AMIs from EC2
            image_as_dicts = retrieve_ec2_data(image_ids, region)
            destination_path = f"moto/ec2/resources/ecs/optimized_amis/{region}.json"
            save_to_file(destination_path, image_as_dicts)

            time.sleep(0.5)
        except botocore.exceptions.ClientError as e:
            print(e)
            # We might encounter an error if we do not have access to a region - just ignore and try the next region


if __name__ == "__main__":
    main()
