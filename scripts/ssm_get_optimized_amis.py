import time
import re
import json
from datetime import timezone
from pathlib import Path

import boto3
import botocore
from loguru import logger

from moto.core.utils import unix_time
from moto.ec2.utils import gen_moto_amis

session = boto3.Session()


@logger.catch()
def retrieve_by_path(client, path):
    logger.info("Attempting to retrieve data for path={}", path)
    try:
        response = client.get_parameters_by_path(Path=path, Recursive=True)
        parameters = response["Parameters"]
        next_token = response["NextToken"]
        while next_token:
            response = client.get_parameters_by_path(Path=path, Recursive=True, NextToken=next_token)
            parameters.extend(response["Parameters"])
            next_token = response.get("NextToken")

        logger.info("Data retrieved from path={}", path)

        return parameters
    except botocore.exceptions.ClientError as e:
        logger.error(e)


@logger.catch()
def save_to_file(destination_path: str, params: dict):
    logger.info("Attempting to save data to {}", destination_path)
    try:
        file_path = Path(Path.cwd(), destination_path)
        file_path.parent.mkdir(exist_ok=True, parents=True)

        with file_path.open("w") as fb:
            json.dump(params, fb, sort_keys=True, indent=2)

        logger.info("Data saved to {}", file_path)
    except Exception as e:
        logger.error(e)


def get_regions():
    try:
        regions = session.get_available_regions("ssm")
        logger.info("Listing all regions={}", regions)

        return regions
    except botocore.exceptions.ClientError as e:
        logger.error(e)


@logger.catch()
def retrieve_ec2_data(parameters: list, region: str):
    try:
        ec2_client = session.client("ec2", region_name=region)

        logger.debug("parameters type: {}", type(parameters))

        image_ids = []

        for parameter in parameters:
            value = parameter.get("Value")

            if isinstance(value, str):
                first_char = value[0]
                last_char = value[-1]

                if first_char == "{" and last_char == "}":
                    value = json.loads(value)
                    image_ids.append(value.get("image_id"))
                else:
                    image_ids.extend(re.findall("ami-[\d\w]{17}", value))

        image_ids = list(set(image_ids))

        logger.debug("Attempting to find all ec2 images for amis={}", image_ids)

        images = ec2_client.describe_images(ImageIds=image_ids)["Images"]

        return gen_moto_amis(images)
    except Exception as e:
        logger.error(e)


@logger.catch()
def main():
    """
    Retrieve the latest AMI-details from SSM
     - Download from AWS
     - Store this in the dedicated moto/ssm/resources-folder
    """
    for region in get_regions():
        ssm_client = session.client('ssm', region_name=region)

        default_param_path = "/aws/service/ecs/optimized-ami"

        # Retrieve default AMI values
        try:
            logger.info("Retrieving data for {}" , region)

            parameters = retrieve_by_path(ssm_client, default_param_path)

            if not parameters:
                logger.warning("Skipping region={}", region)
                continue

            for param in parameters:
                param["LastModifiedDate"] = unix_time(param["LastModifiedDate"].astimezone(timezone.utc).replace(tzinfo=None))

                if isinstance(param["Value"], str) and param["Value"][0] == "{":
                    param["Value"] = json.loads(param["Value"])

            destination_path = f"moto/ssm/resources/ecs/optimized-ami/{region}.json"
            save_to_file(destination_path, parameters)

            # Retrieve details about AMIs from EC2
            image_as_dicts = retrieve_ec2_data(parameters, region)
            destination_path = f"moto/ec2/resources/ecs/optimized-ami/{region}.json"
            save_to_file(destination_path, image_as_dicts)

            time.sleep(0.5)
        except botocore.exceptions.ClientError as e:
            logger.error(e)
            # We might encounter an error if we do not have access to a region - just ignore and try the next region


if __name__ == "__main__":
    main()
