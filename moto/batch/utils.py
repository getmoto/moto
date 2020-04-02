from __future__ import unicode_literals


def make_arn_for_compute_env(account_id, name, region_name):
    return "arn:aws:batch:{0}:{1}:compute-environment/{2}".format(
        region_name, account_id, name
    )


def make_arn_for_job_queue(account_id, name, region_name):
    return "arn:aws:batch:{0}:{1}:job-queue/{2}".format(region_name, account_id, name)


def make_arn_for_task_def(account_id, name, revision, region_name):
    return "arn:aws:batch:{0}:{1}:job-definition/{2}:{3}".format(
        region_name, account_id, name, revision
    )


def lowercase_first_key(some_dict):
    new_dict = {}
    for key, value in some_dict.items():
        new_key = key[0].lower() + key[1:]
        new_dict[new_key] = value

    return new_dict
