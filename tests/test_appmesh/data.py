def route_spec(route: str) -> Dict[str, Any]:  # type: ignore[misc]
    is_first_route = "1" in route
    return {
        "grpcRoute": {
            "action": {
                "weightedTargets": [
                    {"port": 80, "virtualNode": "mock_node", "weight": 100},
                ]
            },
            "match": {
                "metadata": [
                    {
                        "invert": True,
                        "match": {
                            "exact": "TODO",
                            "prefix": "TODO",
                            "range": {"end": 123, "start": 123},
                            "regex": "TODO",
                            "suffix": "TODO",
                        },
                        "name": "TODO",
                    },
                ],
                "methodName": "TODO",
                "port": 123,
                "serviceName": "TODO",
            },
            "retryPolicy": {
                "grpcRetryEvents": [
                    "cancelled",
                    "deadline-exceeded",
                    "internal",
                    "resource-exhausted",
                    "unavailable",
                ],
                "httpRetryEvents": [
                    "TODO",
                ],
                "maxRetries": 123,
                "perRetryTimeout": {"unit": "ms", "value": 100},
                "tcpRetryEvents": [
                    "connection-error",
                ],
            },
            "timeout": {
                "idle": {"unit": "ms", "value": 100},
                "perRequest": {"unit": "ms", "value": 100},
            },
        },
        "http2Route": {
            "action": {
                "weightedTargets": [
                    {"port": 443, "virtualNode": "mock_node", "weight": 100},
                ]
            },
            "match": {
                "headers": [
                    {
                        "invert": False,
                        "match": {
                            "exact": "TODO",
                            "prefix": "TODO",
                            "range": {"end": 1, "start": 100},
                            "regex": "TODO",
                            "suffix": "TODO",
                        },
                        "name": "TODO",
                    },
                ],
                "method": "GET"
                | "HEAD"
                | "POST"
                | "PUT"
                | "DELETE"
                | "CONNECT"
                | "OPTIONS"
                | "TRACE"
                | "PATCH",
                "path": {"exact": "string", "regex": "string"},
                "port": 123,
                "prefix": "string",
                "queryParameters": [
                    {"match": {"exact": "string"}, "name": "string"},
                ],
                "scheme": "http" | "https",
            },
            "retryPolicy": {
                "httpRetryEvents": [
                    "string",
                ],
                "maxRetries": 123,
                "perRetryTimeout": {"unit": "s" | "ms", "value": 123},
                "tcpRetryEvents": [
                    "connection-error",
                ],
            },
            "timeout": {
                "idle": {"unit": "s" | "ms", "value": 123},
                "perRequest": {"unit": "s" | "ms", "value": 123},
            },
        },
        "httpRoute": {
            "action": {
                "weightedTargets": [
                    {"port": 123, "virtualNode": "string", "weight": 123},
                ]
            },
            "match": {
                "headers": [
                    {
                        "invert": True | False,
                        "match": {
                            "exact": "string",
                            "prefix": "string",
                            "range": {"end": 123, "start": 123},
                            "regex": "string",
                            "suffix": "string",
                        },
                        "name": "string",
                    },
                ],
                "method": "GET"
                | "HEAD"
                | "POST"
                | "PUT"
                | "DELETE"
                | "CONNECT"
                | "OPTIONS"
                | "TRACE"
                | "PATCH",
                "path": {"exact": "string", "regex": "string"},
                "port": 123,
                "prefix": "string",
                "queryParameters": [
                    {"match": {"exact": "string"}, "name": "string"},
                ],
                "scheme": "http" | "https",
            },
            "retryPolicy": {
                "httpRetryEvents": [
                    "string",
                ],
                "maxRetries": 123,
                "perRetryTimeout": {"unit": "s" | "ms", "value": 123},
                "tcpRetryEvents": [
                    "connection-error",
                ],
            },
            "timeout": {
                "idle": {"unit": "s" | "ms", "value": 123},
                "perRequest": {"unit": "s" | "ms", "value": 123},
            },
        },
        "priority": 123,
        "tcpRoute": {
            "action": {
                "weightedTargets": [
                    {"port": 123, "virtualNode": "string", "weight": 123},
                ]
            },
            "match": {"port": 123},
            "timeout": {"idle": {"unit": "s" | "ms", "value": 123}},
        },
    }
