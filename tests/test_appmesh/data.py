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

#TODO Need to add to connection pool
virtual_node_spec_1 = {
    'backendDefaults': {
        'clientPolicy': {
            'tls': {
                'certificate': {
                    'file': {
                        'certificateChain': '/path/to/cert_chain.pem',
                        'privateKey': '/path/to/private_key.pem'
                    }
                },
                'enforce': True,
                'ports': [443],
                'validation': {
                    'subjectAlternativeNames': {
                        'match': {
                            'exact': ['www.example.com', 'api.example.com']
                        }
                    },
                    'trust': {
                        'file': {
                            'certificateChain': '/path/to/ca_bundle.pem'
                        }
                    }
                }
            }
        }
    },
    'backends': [
        {
            'virtualService': {
                'clientPolicy': {
                    'tls': {
                        'enforce': False
                    }
                },
                'virtualServiceName': 'my-service.default.svc.cluster.local'
            }
        }
    ],
    'listeners': [
        {
            'connectionPool': {
                'http': {
                    'maxConnections': 1000,
                    'maxPendingRequests': 5000
                }
            },
            'healthCheck': {
                'healthyThreshold': 2,
                'intervalMillis': 5000,
                'path': '/health',
                'port': 80,
                'protocol': 'http',
                'timeoutMillis': 2000,
                'unhealthyThreshold': 3
            },
            'outlierDetection': {
                'baseEjectionDuration': {
                    'unit': 's',
                    'value': 30
                },
                'interval': {
                    'unit': 's',
                    'value': 10
                },
                'maxEjectionPercent': 10,
                'maxServerErrors': 5
            },
            'portMapping': {
                'port': 80,
                'protocol': 'http'
            },
            'timeout': {
                'http': {
                    'idle': {
                        'unit': 's',
                        'value': 60
                    },
                    'perRequest': {
                        'unit': 's',
                        'value': 5
                    }
                }
            },
            'tls': {
                'certificate': {
                    'acm': {
                        'certificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/abcdefg-1234-5678-90ab-cdef01234567'
                    }
                },
                'mode': 'STRICT',
                'validation': {
                    'trust': {
                        'sds': {
                            'secretName': 'my-ca-bundle-secret'
                        }
                    }
                }
            }
        }
    ],
    'logging': {
        'accessLog': {
            'file': {
                'format': {
                    'json': [
                        {
                            'key': 'start_time',
                            'value': '%START_TIME%'
                        },
                        {
                            'key': 'method',
                            'value': '%REQ(:METHOD)%'
                        }
                    ]
                },
                'path': '/var/log/appmesh/access.log'
            }
        }
    },
    'serviceDiscovery': {
        'awsCloudMap': {
            'attributes': [
                {
                    'key': 'env',
                    'value': 'prod'
                }
            ],
            'ipPreference': 'IPv4_PREFERRED',
            'namespaceName': 'my-namespace',
            'serviceName': 'my-service'
        }
    }
}

virtual_node_spec_2 = {
    'backendDefaults': {
        'clientPolicy': {
            'tls': {
                'certificate': {
                    'file': {
                        'certificateChain': '/new/path/to/cert_chain.pem',
                        'privateKey': '/new/path/to/private_key.pem'
                    }
                },
                'enforce': False,
                'ports': [8443],
                'validation': {
                    'subjectAlternativeNames': {
                        'match': {
                            'exact': ['new.example.com', 'dev.example.com']
                        }
                    },
                    'trust': {
                        'file': {
                            'certificateChain': '/new/path/to/ca_bundle.pem'
                        }
                    }
                }
            }
        }
    },
    'backends': [
        {
            'virtualService': {
                'clientPolicy': {
                    'tls': {
                        'enforce': True
                    }
                },
                'virtualServiceName': 'another-service.default.svc.cluster.local'
            }
        }
    ],
    'listeners': [
        {
            'connectionPool': {
                'http': {
                    'maxConnections': 2000,
                    'maxPendingRequests': 10000
                }
            },
            'healthCheck': {
                'healthyThreshold': 3,
                'intervalMillis': 10000,
                'path': '/status',
                'port': 8080,
                'protocol': 'https',
                'timeoutMillis': 3000,
                'unhealthyThreshold': 2
            },
            'outlierDetection': {
                'baseEjectionDuration': {
                    'unit': 'ms',
                    'value': 500
                },
                'interval': {
                    'unit': 'm',
                    'value': 1
                },
                'maxEjectionPercent': 5,
                'maxServerErrors': 10
            },
            'portMapping': {
                'port': 8080,
                'protocol': 'https'
            },
            'timeout': {
                'http': {
                    'idle': {
                        'unit': 'm',
                        'value': 5
                    },
                    'perRequest': {
                        'unit': 'ms',
                        'value': 1000
                    }
                }
            },
            'tls': {
                'certificate': {
                    'acm': {
                        'certificateArn': 'arn:aws:acm:us-west-2:987654321098:certificate/hgfedcba-4321-8765-09ba-fedc09876543'
                    }
                },
                'mode': 'PERMISSIVE',
                'validation': {
                    'trust': {
                        'sds': {
                            'secretName': 'another-ca-bundle-secret'
                        }
                    }
                }
            }
        }
    ],
    'logging': {
        'accessLog': {
            'file': {
                'format': {
                    'json': [
                        {
                            'key': 'end_time',
                            'value': '%END_TIME%'
                        },
                        {
                            'key': 'status_code',
                            'value': '%RESPONSE_CODE%'
                        }
                    ]
                },
                'path': '/var/log/appmesh/new_access.log'
            }
        }
    },
    'serviceDiscovery': {
        'awsCloudMap': {
            'attributes': [
                {
                    'key': 'region',
                    'value': 'us-east-1'
                }
            ],
            'ipPreference': 'IPv6_PREFERRED',
            'namespaceName': 'new-namespace',
            'serviceName': 'new-service'
        }
    }
}