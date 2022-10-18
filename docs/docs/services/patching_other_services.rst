.. _patching_other_services:


=======================
Patching other Services
=======================

Since ``moto`` does not support every AWS service available there is a way to patch ``boto3`` calls until they are supported.

To do so, you need to mock the ``botocore.client.BaseClient._make_api_call`` function using `mock.patch <https://docs.python.org/3/library/unittest.mock.html#patch>`_:

.. sourcecode:: python

    import boto3
    import botocore
    from unittest.mock import patch

    # Original botocore _make_api_call function
    orig = botocore.client.BaseClient._make_api_call
    
    # Mocked botocore _make_api_call function
    def mock_make_api_call(self, operation_name, kwarg):
        # For example for the Access Analyzer service
        # As you can see the operation_name has the list_analyzers snake_case form but
        # we are using the ListAnalyzers form.
        # Rationale -> https://github.com/boto/botocore/blob/develop/botocore/client.py#L810:L816
        if operation_name == 'ListAnalyzers':
            return { "analyzers": 
                [{
                    "arn": "ARN", 
                    "name": "Test Analyzer" , 
                    "status": "Enabled", 
                    "findings": 0, 
                    "tags":"", 
                    "type": "ACCOUNT", 
                    "region": "eu-west-1"
                    }
                ]}
        # If we don't want to patch the API call
        return orig(self, operation_name, kwarg)


    def test_list_findings():
        client = boto3.client("accessanalyzer")

        with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
            analyzers_list = client.list_analyzers()
            assert len(analyzers_list["analyzers"]) == 1
            # include your assertions here


Note that this does not use Moto, to keep it simple, but if you use any ``moto``-decorators in addition to the patch, the call to ``orig(self, operation_name, kwarg)`` will be intercepted by Moto.
