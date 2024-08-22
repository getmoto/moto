def route_spec(route: str) -> Dict[str, Any]: # type: ignore[misc]
    is_first_route = "1" in route
    return {
        'grpcRoute': {
            'action': {
                'weightedTargets': [
                    {
                        'port': 80,
                        'virtualNode': 'mock_node',
                        'weight': 100
                    },
                ]
            },
            'match': {
                'metadata': [
                    {
                        'invert': True,
                        'match': {
                            'exact': 'string',
                            'prefix': 'string',
                            'range': {
                                'end': 123,
                                'start': 123
                            },
                            'regex': 'string',
                            'suffix': 'string'
                        },
                        'name': 'string'
                    },
                ],
                'methodName': 'string',
                'port': 123,
                'serviceName': 'string'
            },
            'retryPolicy': {
                'grpcRetryEvents': [
                    'cancelled'|'deadline-exceeded'|'internal'|'resource-exhausted'|'unavailable',
                ],
                'httpRetryEvents': [
                    'string',
                ],
                'maxRetries': 123,
                'perRetryTimeout': {
                    'unit': 's'|'ms',
                    'value': 123
                },
                'tcpRetryEvents': [
                    'connection-error',
                ]
            },
            'timeout': {
                'idle': {
                    'unit': 's'|'ms',
                    'value': 123
                },
                'perRequest': {
                    'unit': 's'|'ms',
                    'value': 123
                }
            }
        },
        'http2Route': {
            'action': {
                'weightedTargets': [
                    {
                        'port': 123,
                        'virtualNode': 'string',
                        'weight': 123
                    },
                ]
            },
            'match': {
                'headers': [
                    {
                        'invert': True|False,
                        'match': {
                            'exact': 'string',
                            'prefix': 'string',
                            'range': {
                                'end': 123,
                                'start': 123
                            },
                            'regex': 'string',
                            'suffix': 'string'
                        },
                        'name': 'string'
                    },
                ],
                'method': 'GET'|'HEAD'|'POST'|'PUT'|'DELETE'|'CONNECT'|'OPTIONS'|'TRACE'|'PATCH',
                'path': {
                    'exact': 'string',
                    'regex': 'string'
                },
                'port': 123,
                'prefix': 'string',
                'queryParameters': [
                    {
                        'match': {
                            'exact': 'string'
                        },
                        'name': 'string'
                    },
                ],
                'scheme': 'http'|'https'
            },
            'retryPolicy': {
                'httpRetryEvents': [
                    'string',
                ],
                'maxRetries': 123,
                'perRetryTimeout': {
                    'unit': 's'|'ms',
                    'value': 123
                },
                'tcpRetryEvents': [
                    'connection-error',
                ]
            },
            'timeout': {
                'idle': {
                    'unit': 's'|'ms',
                    'value': 123
                },
                'perRequest': {
                    'unit': 's'|'ms',
                    'value': 123
                }
            }
        },
        'httpRoute': {
            'action': {
                'weightedTargets': [
                    {
                        'port': 123,
                        'virtualNode': 'string',
                        'weight': 123
                    },
                ]
            },
            'match': {
                'headers': [
                    {
                        'invert': True|False,
                        'match': {
                            'exact': 'string',
                            'prefix': 'string',
                            'range': {
                                'end': 123,
                                'start': 123
                            },
                            'regex': 'string',
                            'suffix': 'string'
                        },
                        'name': 'string'
                    },
                ],
                'method': 'GET'|'HEAD'|'POST'|'PUT'|'DELETE'|'CONNECT'|'OPTIONS'|'TRACE'|'PATCH',
                'path': {
                    'exact': 'string',
                    'regex': 'string'
                },
                'port': 123,
                'prefix': 'string',
                'queryParameters': [
                    {
                        'match': {
                            'exact': 'string'
                        },
                        'name': 'string'
                    },
                ],
                'scheme': 'http'|'https'
            },
            'retryPolicy': {
                'httpRetryEvents': [
                    'string',
                ],
                'maxRetries': 123,
                'perRetryTimeout': {
                    'unit': 's'|'ms',
                    'value': 123
                },
                'tcpRetryEvents': [
                    'connection-error',
                ]
            },
            'timeout': {
                'idle': {
                    'unit': 's'|'ms',
                    'value': 123
                },
                'perRequest': {
                    'unit': 's'|'ms',
                    'value': 123
                }
            }
        },
        'priority': 123,
        'tcpRoute': {
            'action': {
                'weightedTargets': [
                    {
                        'port': 123,
                        'virtualNode': 'string',
                        'weight': 123
                    },
                ]
            },
            'match': {
                'port': 123
            },
            'timeout': {
                'idle': {
                    'unit': 's'|'ms',
                    'value': 123
                }
            }
        }
    }