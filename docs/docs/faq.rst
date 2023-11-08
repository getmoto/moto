.. _contributing faq:

.. role:: raw-html(raw)
    :format: html


======
FAQ
======

Is Moto concurrency safe?
############################

No. Moto is not designed for multithreaded access/multiprocessing.

Why am I getting RUST errors when installing Moto?
####################################################

Moto has a dependency on the pip-module `cryptography`. As of Cryptography >= 3.4, this module requires Rust as a dependency. :raw-html:`<br />`
Most OS/platforms will support the installation of Rust, but if you're getting any errors related to this, see the cryptography documentation for more information: https://cryptography.io/en/latest/installation/#rust

Can I mock the default AWS region?
###################################

By default, Moto only allows valid regions, supporting the same regions that AWS supports.

If you want to mock the default region, as an additional layer of protection against accidentally touching your real AWS environment, you can disable this validation:

.. sourcecode:: python

    os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = True
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
