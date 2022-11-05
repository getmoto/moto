from typing import Any, Dict


def make_arn_for_compute_env(account_id: str, name: str, region_name: str) -> str:
    return "arn:aws:batch:{0}:{1}:compute-environment/{2}".format(
        region_name, account_id, name
    )


def make_arn_for_job_queue(account_id: str, name: str, region_name: str) -> str:
    return "arn:aws:batch:{0}:{1}:job-queue/{2}".format(region_name, account_id, name)


def make_arn_for_task_def(
    account_id: str, name: str, revision: int, region_name: str
) -> str:
    return "arn:aws:batch:{0}:{1}:job-definition/{2}:{3}".format(
        region_name, account_id, name, revision
    )


def lowercase_first_key(some_dict: Dict[str, Any]) -> Dict[str, Any]:
    new_dict: Dict[str, Any] = {}
    for key, value in some_dict.items():
        new_key = key[0].lower() + key[1:]
        try:
            if isinstance(value, dict):
                new_dict[new_key] = lowercase_first_key(value)
            elif all([isinstance(v, dict) for v in value]):
                new_dict[new_key] = [lowercase_first_key(v) for v in value]
            else:
                new_dict[new_key] = value
        except TypeError:
            new_dict[new_key] = value

    return new_dict
