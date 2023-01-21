import json
from typing import Any


class DynamoJsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, "to_json"):
            return o.to_json()


def dynamo_json_dump(dynamo_object: Any) -> str:
    return json.dumps(dynamo_object, cls=DynamoJsonEncoder)


def bytesize(val: str) -> int:
    return len(val.encode("utf-8"))
