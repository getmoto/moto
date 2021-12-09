.. _contributing tips:


.. role:: raw-html(raw)
    :format: html


=============================
Development Tips
=============================

Below you can find some tips that might help during development.

Naming Conventions
****************************

Let's say you want to implement the `import_certificate` feature for the ACM service.

Implementing the feature itself can be done by creating a method called `import_certificate` in `moto/acm/responses.py`. :raw-html:`<br />`
It's considered good practice to deal with input/output formatting and validation in `responses.py`, and create a method `import_certificate` in `moto/acm/models.py` that handles the actual import logic.

When writing tests, you'll want to add a new method called `def test_import_certificate` to `tests/test_acm/test_acm.py`. :raw-html:`<br />`
Additional tests should also have names indicate of what's happening, i.e. `def test_import_certificate_fails_without_name`, `def test_import_existing_certificate`, etc.



Partial Implementations
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a service is only partially implemented, a warning can be used to inform the user:

.. sourcecode:: python

  import warnings
  warnings.warn("The Filters-parameter is not yet implemented for client.method()")

