.. _multi_account:

=====================
Multi-Account support
=====================


Moto processes all requests in a default account, `12345678910`. The exact credentials provided are ignored to make the process of getting started with Moto as hassle-free as possible.

There are two ways to change the account ID - assuming a role using STS, or overriding the account ID using an environment variable.

Configure an account using STS
------------------------------

The `STS.assume_role()`-feature is useful if you want to temporarily use a different set of access credentials.
Passing in a role that belongs to a different account will return a set of credentials that give access to that account.

.. note::

    If you pass in a RoleARN with a non-existing account, Moto will create it for you.

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

Configure an account using environment variables
------------------------------------------------

It is possible to configure the environment variable `MOTO_ACCOUNT_ID` - any requests afterwards will use that account ID.

.. sourcecode:: python

    # Create a bucket in the default account
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="bucket-default-account")

    # Create another bucket in another account
    os.environ["MOTO_ACCOUNT_ID"] = "111111111111"
    client.create_bucket(Bucket="bucket-in-account-2")

    assert [b["Name"] for b in client2.list_buckets()["Buckets"]] == ["bucket-in-account-2"]

    # Switch to the default account to read the first bucket
    del os.environ["MOTO_ACCOUNT_ID"]
    assert [b["Name"] for b in client2.list_buckets()["Buckets"]] == ["bucket-default-account"]

