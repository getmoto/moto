.. _multi_account:

=====================
Multi-Account support
=====================


By default, Moto processes all requests in a default account: `123456789012`. The exact credentials provided are usually ignored to make the process of mocking requests as hassle-free as possible.

If you want to mock resources in multiple accounts, or you want to change the default account ID, there are multiple ways to achieve this.

Configure the default account
------------------------------

It is possible to configure the default account ID that will be used for all incoming requests, by setting the environment variable `MOTO_ACCOUNT_ID`.

Here is an example of what this looks like in practice:

.. sourcecode:: python

    # Create a bucket in the default account
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="bucket-default-account")

    # Configure another account - all subsequent requests will use this account ID
    os.environ["MOTO_ACCOUNT_ID"] = "111111111111"
    client.create_bucket(Bucket="bucket-in-account-2")

    assert [b["Name"] for b in client2.list_buckets()["Buckets"]] == ["bucket-in-account-2"]

    # Now revert to the default account, by removing the environment variable
    del os.environ["MOTO_ACCOUNT_ID"]
    assert [b["Name"] for b in client2.list_buckets()["Buckets"]] == ["bucket-default-account"]



Configure the account ID using a request header
---------------------------------------------------

If you are using Moto in ServerMode you can add a custom header to a request, to specify which account should be used.

.. note::

    Moto will only look at the request-header if the environment variable is not set.

As an example, this is how you would create an S3-bucket in another account:

.. sourcecode:: python

    headers ={"x-moto-account-id": "333344445555"}
    requests.put("http://bucket.localhost:5000/", headers=headers)

    # This will return a list of all buckets in account 333344445555
    requests.get("http://localhost:5000", headers=headers)

    # This will return an empty list, as there are no buckets in the default account
    requests.get("http://localhost:5000")

Configure an account using STS
------------------------------

The `STS.assume_role()`-feature is useful if you want to temporarily use a different set of access credentials.
Passing in a role that belongs to a different account will return a set of credentials that give access to that account.

.. note::

    To avoid any chicken-and-egg problems trying to create roles in non-existing accounts, these Roles do not need to exist.
    Moto will only extract the account ID from the role, and create access credentials for that account.

.. note::

    Moto will only look at the access credentials if the environment variable and request header is not set.

Let's look at some examples.


.. sourcecode:: python

    # Create a bucket using the default access credentials
    client1 = boto3.client("s3", region_name="us-east-1")
    client1.create_bucket(Bucket="foobar")

    # Assume a role in our account
    # Note that this Role does not need to exist
    default_account = "123456789012"
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn=f"arn:aws:iam::{default_account}:role/my-role",
        RoleSessionName="test-session-name",
        ExternalId="test-external-id",
    )

    # These access credentials give access to the default account
    client2 = boto3.client(
        "s3",
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
        region_name="us-east-1",
    )
    client2.list_buckets()["Buckets"].should.have.length_of(1)

Because we assumed a role within the same account, we can see the bucket that we've just created.

Things get interesting when assuming a role within a different account.

.. sourcecode:: python

    # Create a bucket with default access credentials
    client1 = boto3.client("s3", region_name="us-east-1")
    client1.create_bucket(Bucket="foobar")

    # Assume a role in a different account
    # Note that the Role does not need to exist
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn="arn:aws:iam::111111111111:role/role-in-another-account",
        RoleSessionName="test-session-name",
        ExternalId="test-external-id",
    )

    # Retrieve all buckets in this new account - this will be completely empty
    client2 = boto3.client(
        "s3",
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
        region_name="us-east-1",
    )
    client2.list_buckets()["Buckets"].should.have.length_of(0)

Because we've assumed a role in a different account, no buckets were found. The `foobar`-bucket only exists in the default account, not in `111111111111`.

