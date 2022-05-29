import json


_EVENT_S3_OBJECT_CREATED = {
    "version": "0",
    "id": "17793124-05d4-b198-2fde-7ededc63b103",
    "detail-type": "Object Created",
    "source": "aws.s3",
    "account": "123456789012",
    "time": "2021-11-12T00:00:00Z",
    "region": None,
    "resources": [],
    "detail": None,
}


def send_notification(source, event_name, region, resources, detail):
    try:
        _send_safe_notification(source, event_name, region, resources, detail)
    except:  # noqa
        # If anything goes wrong, we should never fail
        pass


def _send_safe_notification(source, event_name, region, resources, detail):
    from .models import events_backends

    event = None
    if source == "aws.s3" and event_name == "CreateBucket":
        event = _EVENT_S3_OBJECT_CREATED.copy()
        event["region"] = region
        event["resources"] = resources
        event["detail"] = detail

    if event is None:
        return

    for backend in events_backends.values():
        applicable_targets = []
        for rule in backend.rules.values():
            if rule.state != "ENABLED":
                continue
            pattern = rule.event_pattern.get_pattern()
            if source in pattern.get("source", []):
                if event_name in pattern.get("detail", {}).get("eventName", []):
                    applicable_targets.extend(rule.targets)

        for target in applicable_targets:
            if target.get("Arn", "").startswith("arn:aws:lambda"):
                _invoke_lambda(target.get("Arn"), event=event)


def _invoke_lambda(fn_arn, event):
    from moto.awslambda import lambda_backends

    lmbda_region = fn_arn.split(":")[3]

    body = json.dumps(event)
    lambda_backends[lmbda_region].invoke(
        function_name=fn_arn,
        qualifier=None,
        body=body,
        headers=dict(),
        response_headers=dict(),
    )
