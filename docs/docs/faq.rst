.. _contributing faq:

.. role:: raw-html(raw)
    :format: html


======
FAQ
======

Why is my test data disappearing?
###################################
To prevent state from leaking across different tests, Moto automatically deletes any created data after a Moto-decorator ends.

So make sure that your decorator is active for the entire duration of the test-method.

Is Moto concurrency safe?
############################

No. Moto is not designed for multithreaded access/multiprocessing.

Moto's internal state, encompassing resource creations and modifications, is managed within the context of the thread in which it is invoked. In a multithreading environment, Python's threading model involves creating a new thread that initially copies the global context from the main thread. However, it's crucial to understand that this copy is a one-time snapshot at the moment of thread creation.

If Moto is employed to mock AWS services in a secondary thread, resources created or modified within that thread may not be visible to other threads or the main thread. The initial copy of the global context to the new thread means that the secondary thread depends on the state from the main thread in a read-only manner. Subsequent modifications or creations within the secondary thread do not propagate back to the main thread or affect the global context of other threads.

For example, if you are using Moto to mock the AWS Cognito IDP service and create users, and these operations are performed in a thread separate from the main application logic, the application may not be able to see the users created in the secondary thread. This limitation arises because, in Python, the new thread's initial state is a copy of the main thread's state, and any changes in one thread do not automatically reflect in other threads and vice versa.

It is essential to consider this behavior when using Moto in scenarios involving multiple threads. For tests that require resource modifications, such as creating or updating AWS resources, it is recommended to ensure that Moto operations are performed within the same thread context as the application or test logic to ensure consistent behavior.

Why am I getting RUST errors when installing Moto?
####################################################

Moto has a dependency on the pip-module `cryptography`. As of Cryptography >= 3.4, this module requires Rust as a dependency. :raw-html:`<br />`
Most OS/platforms will support the installation of Rust, but if you're getting any errors related to this, see the cryptography documentation for more information: https://cryptography.io/en/latest/installation/#rust

Can I mock the default AWS region?
###################################

By default, Moto only allows valid regions, supporting the same regions that AWS supports.

If you want to mock the default region, as an additional layer of protection against accidentally touching your real AWS environment, you can disable this validation:

.. sourcecode:: python

    os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "True"
    os.environ["AWS_DEFAULT_REGION"] = "antarctica"


How can I mock my own HTTP-requests, using the Responses-module?
################################################################

Moto uses it's own Responses-mock to intercept AWS requests, so if you need to intercept custom (non-AWS) request as part of your tests, you may find that Moto 'swallows' any pass-thru's that you have defined.
You can pass your own Responses-mock to Moto, to ensure that any custom (non-AWS) are handled by that Responses-mock.

.. sourcecode:: python

    from moto.core.models import override_responses_real_send

    my_own_mock = responses.RequestsMock(assert_all_requests_are_fired=True)
    override_responses_real_send(my_own_mock)
    my_own_mock.start()
    my_own_mock.add_passthru("http://some-website.com")

    # Unset this behaviour at the end of your tests
    override_responses_real_send(None)
