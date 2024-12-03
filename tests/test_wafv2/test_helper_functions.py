def CREATE_WEB_ACL_BODY(name: str, scope: str) -> dict:
    return {
        "Scope": scope,
        "Name": name,
        "DefaultAction": {"Allow": {}},
        "VisibilityConfig": {
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "idk",
        },
    }
