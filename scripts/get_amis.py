import boto3
import json

from moto.ec2.utils import gen_moto_amis

# Taken from free tier list when creating an instance
instances = [
    "ami-760aaa0f",
    "ami-bb9a6bc2",
    "ami-35e92e4c",
    "ami-785db401",
    "ami-b7e93bce",
    "ami-dca37ea5",
    "ami-999844e0",
    "ami-9b32e8e2",
    "ami-f8e54081",
    "ami-bceb39c5",
    "ami-03cf127a",
    "ami-1ecc1e67",
    "ami-c2ff2dbb",
    "ami-12c6146b",
    "ami-d1cb19a8",
    "ami-61db0918",
    "ami-56ec3e2f",
    "ami-84ee3cfd",
    "ami-86ee3cff",
    "ami-f0e83a89",
    "ami-1f12c066",
    "ami-afee3cd6",
    "ami-1812c061",
    "ami-77ed3f0e",
    "ami-3bf32142",
    "ami-6ef02217",
    "ami-f4cf1d8d",
    "ami-3df32144",
    "ami-c6f321bf",
    "ami-24f3215d",
    "ami-fa7cdd89",
    "ami-1e749f67",
    "ami-a9cc1ed0",
    "ami-8104a4f8",
]

client = boto3.client("ec2", region_name="eu-west-1")

test = client.describe_images(ImageIds=instances)

result = gen_moto_amis(test["Images"])

print(json.dumps(result, indent=2))
