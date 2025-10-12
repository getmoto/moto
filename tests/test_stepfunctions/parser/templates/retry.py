retry_template = {
    "Comment": "RETRY_INTERVAL_FEATURES",
    "StartAt": "LambdaTask",
    "States": {
        "LambdaTask": {
            "Type": "Task",
            "Resource": "_tbd_",
            "End": True,
            "Retry": [
                {
                    "Comment": "Includes all retry language features.",
                    "ErrorEquals": ["States.ALL"],
                    "IntervalSeconds": 2,
                    "MaxAttempts": 2,
                    "BackoffRate": 1,
                    "MaxDelaySeconds": 5,
                    "JitterStrategy": "FULL",
                }
            ],
        }
    },
}
