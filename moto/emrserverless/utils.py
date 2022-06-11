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


def default_auto_start_configuration():
    return {"enabled": True}


def default_auto_stop_configuration():
    return {"enabled": True, "idleTimeoutMinutes": 15}


def paginated_list(full_list, sort_key, max_results, next_token):
    """
    Returns a tuple containing a slice of the full list starting at next_token and ending with at most the max_results
    number of elements, and the new next_token which can be passed back in for the next segment of the full list.
    """
    if next_token is None or not next_token:
        next_token = 0
    next_token = int(next_token)

    sorted_list = sorted(full_list, key=lambda d: d[sort_key])

    values = sorted_list[next_token : next_token + max_results]
    if len(values) == max_results:
        new_next_token = str(next_token + max_results)
    else:
        new_next_token = None
    return values, new_next_token
