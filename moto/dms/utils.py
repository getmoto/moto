from __future__ import unicode_literals


def match_task_arn(task, arns):
    return task["ReplicationTaskArn"] in arns


def match_task_id(task, ids):
    return task["ReplicationTaskIdentifier"] in ids


def match_task_migration_type(task, migration_types):
    return task["MigrationType"] in migration_types


def match_task_endpoint_arn(task, endpoint_arns):
    return (
        task["SourceEndpointArn"] in endpoint_arns
        or task["TargetEndpointArn"] in endpoint_arns
    )


def match_task_replication_instance_arn(task, replication_instance_arns):
    return task["ReplicationInstanceArn"] in replication_instance_arns


task_filter_functions = {
    "replication-task-arn": match_task_arn,
    "replication-task-id": match_task_id,
    "migration-type": match_task_migration_type,
    "endpoint-arn": match_task_endpoint_arn,
    "replication-instance-arn": match_task_replication_instance_arn,
}


def filter_tasks(tasks, filters):
    matching_tasks = tasks

    for f in filters:
        filter_function = task_filter_functions[f["Name"]]

        if not filter_function:
            continue

        matching_tasks = filter(
            lambda task: filter_function(task, f["Values"]), matching_tasks
        )

    return matching_tasks
