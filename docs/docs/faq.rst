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
