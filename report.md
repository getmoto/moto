# Report of the list_jobs issue


## Misbehavior of the list_jobs when filter is provided

Acording to the official documentation, when `filters` is provided, the jobStatus is not taken into account: 

>The filter to apply to the query. Only one filter can be used at a time. When the filter is used, jobStatus is ignored.

But in the logic implemented on the Batch backend, the jobs are also filered by jobStatus 

```Python
# Lines 1873 to 1889 of `batch/models.py`
        for job in jobs_to_check:
            if job_status is not None and job.status != job_status:
                continue

            if filters is not None:
                matches = True
                for filt in filters:
                    name = filt["name"]
                    values = filt["values"]
                    if name == "JOB_NAME":
                        if job.job_name not in values:
                            matches = False
                            break
                if not matches:
                    continue

            jobs.append(job)
```

Also, the boto3 package does not allow to provide `filter` parameter for a list of array jobs

>The filter doesn’t apply to child jobs in an array or multi-node parallel (MNP) jobs.

Meanwhile, in the code, first all jobs are collected (independently if they are batch array jobs or queue jobs) and then all filters are applied.

