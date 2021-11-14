.. _iam access control:

=======================
IAM-like Access Control
=======================

Moto also has the ability to authenticate and authorize actions, just like it's done by IAM in AWS. This functionality can be enabled by either setting the `INITIAL_NO_AUTH_ACTION_COUNT` environment variable or using the `set_initial_no_auth_action_count` decorator. Note that the current implementation is very basic, see `the source code <https://github.com/spulec/moto/blob/master/moto/core/access_control.py>`_ for more information.

`INITIAL_NO_AUTH_ACTION_COUNT`
------------------------------

If this environment variable is set, moto will skip performing any authentication as many times as the variable's value, and only starts authenticating requests afterwards. If it is not set, it defaults to infinity, thus moto will never perform any authentication at all.

`set_initial_no_auth_action_count`
----------------------------------

This is a decorator that works similarly to the environment variable, but the settings are only valid in the function's scope. When the function returns, everything is restored.

.. sourcecode:: python

    @set_initial_no_auth_action_count(4)
    @mock_ec2
    def test_describe_instances_allowed():
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "ec2:Describe*",
                    "Resource": "*"
                }
            ]
        }
        access_key = ...
        # create access key for an IAM user/assumed role that has the policy above.
        # this part should call __exactly__ 4 AWS actions, so that authentication and authorization starts exactly after this

        client = boto3.client('ec2', region_name='us-east-1',
                              aws_access_key_id=access_key['AccessKeyId'],
                              aws_secret_access_key=access_key['SecretAccessKey'])

        # if the IAM principal whose access key is used, does not have the permission to describe instances, this will fail
        instances = client.describe_instances()['Reservations'][0]['Instances']
        assert len(instances) == 0


See `the related test suite <https://github.com/spulec/moto/blob/master/tests/test_core/test_auth.py>`_ for more examples.