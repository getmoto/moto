grpc_route_spec = {
    "priority": 1,
    "grpcRoute": {
        "action": {
            "weightedTargets": [
                {"port": 8080, "virtualNode": "my-virtual-node", "weight": 50}
            ]
        },
        "match": {
            "metadata": [
                {
                    "invert": False,
                    "match": {"exact": "example-value"},
                    "name": "my-metadata-key",
                }
            ],
            "methodName": "myMethod",
            "port": 8080,
            "serviceName": "myService",
        },
        "retryPolicy": {
            "grpcRetryEvents": ["unavailable", "resource-exhausted"],
            "httpRetryEvents": ["gateway-error"],
            "maxRetries": 3,
            "perRetryTimeout": {"unit": "ms", "value": 200},
            "tcpRetryEvents": ["connection-error"],
        },
        "timeout": {
            "idle": {"unit": "s", "value": 60},
            "perRequest": {"unit": "s", "value": 5},
        },
    },
}

http_route_spec = {
    "priority": 2,
    "httpRoute": {
        "action": {
            "weightedTargets": [
                {"port": 80, "virtualNode": "web-server-node", "weight": 100}
            ]
        },
        "match": {
            "headers": [
                {
                    "invert": True,
                    "match": {"prefix": "Bearer "},
                    "name": "Authorization",
                }
            ],
            "method": "POST",
            "path": {"exact": "/login"},
            "port": 80,
            "queryParameters": [
                {"match": {"exact": "example-match"}, "name": "http-query-param"}
            ],
            "scheme": "http",
        },
        "retryPolicy": {
            "httpRetryEvents": ["gateway-error", "client-error"],
            "maxRetries": 0,
            "perRetryTimeout": {"unit": "ms", "value": 0},
            "tcpRetryEvents": ["connection-error"],
        },
        "timeout": {
            "idle": {"unit": "s", "value": 15},
            "perRequest": {"unit": "s", "value": 1},
        },
    },
}

http2_route_spec = {
    "priority": 3,
    "http2Route": {
        "action": {
            "weightedTargets": [
                {"port": 80, "virtualNode": "web-server-node", "weight": 75}
            ]
        },
        "match": {
            "headers": [
                {
                    "invert": False,
                    "match": {"exact": "application/json"},
                    "name": "Content-Type",
                }
            ],
            "method": "GET",
            "path": {"exact": "/api/products"},
            "port": 80,
            "prefix": "/api",
            "queryParameters": [
                {"match": {"exact": "electronics"}, "name": "category"}
            ],
            "scheme": "https",
        },
        "retryPolicy": {
            "httpRetryEvents": ["server-error"],
            "maxRetries": 2,
            "perRetryTimeout": {"unit": "ms", "value": 500},
            "tcpRetryEvents": ["connection-error"],
        },
        "timeout": {
            "idle": {"unit": "s", "value": 30},
            "perRequest": {"unit": "s", "value": 2},
        },
    },
}

tcp_route_spec = {
    "priority": 4,
    "tcpRoute": {
        "action": {
            "weightedTargets": [
                {"port": 22, "virtualNode": "ssh-server-node", "weight": 100}
            ]
        },
        "match": {"port": 22},
        "timeout": {"idle": {"unit": "s", "value": 600}},
    },
}

modified_http_route_spec = {
    "priority": 5,
    "httpRoute": {
        "action": {
            "weightedTargets": [
                {"port": 8080, "virtualNode": "api-server-node", "weight": 50}
            ]
        },
        "match": {
            "headers": [
                {
                    "invert": False,
                    "match": {"prefix": "Token "},
                    "name": "X-Auth-Token",
                }
            ],
            "method": "GET",
            "path": {"exact": "/profile"},
            "port": 443,
            "queryParameters": [
                {"match": {"exact": "modified-match"}, "name": "filter-param"}
            ],
            "scheme": "https",
        },
        "retryPolicy": {
            "httpRetryEvents": ["server-error"],
            "maxRetries": 3,
            "perRetryTimeout": {"unit": "s", "value": 2},
            "tcpRetryEvents": ["connection-reset"],
        },
        "timeout": {
            "idle": {"unit": "m", "value": 5},
            "perRequest": {"unit": "ms", "value": 500},
        },
    },
}
