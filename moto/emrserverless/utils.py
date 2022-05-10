# import json
import random
import string


def get_partition(region):
    return "aws"


def random_id(size=13):
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def random_appplication_id():
    return random_id(size=16)


def random_job_id():
    return random_id(size=16)


def default_capacity_for_type(application_type):
    if application_type == "SPARK":
        return {
            "DRIVER": {
                "workerCount": 2,
                "resourceConfiguration": {
                    "cpu": "2 vCPU",
                    "memory": "4 GB",
                    "disk": "21 GB",
                },
            },
            "EXECUTOR": {
                "workerCount": 10,
                "resourceConfiguration": {
                    "cpu": "4 vCPU",
                    "memory": "4 GB",
                    "disk": "21 GB",
                },
            },
        }
    elif application_type == "HIVE":
        return {
            "DRIVER": {
                "workerCount": 1,
                "resourceConfiguration": {
                    "cpu": "2 vCPU",
                    "memory": "4 GB",
                    "disk": "30 GB",
                },
            },
            "TEZ_TASK": {
                "workerCount": 10,
                "resourceConfiguration": {
                    "cpu": "4 vCPU",
                    "memory": "8 GB",
                    "disk": "30 GB",
                },
            },
        }


def default_max_capacity():
    return {
        "cpu": "400 vCPU",
        "memory": "1024 GB",
        "disk": "1000 GB",
    }
