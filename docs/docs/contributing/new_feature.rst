.. _contributing feature:

=============================
New Features
=============================

Moto has a script that can automatically provide the scaffolding for a new service, and for adding new features to an existing service. This script does all the heavy lifting of generating template code, by looking up the API specification of a given `boto3` method and adding the necessary code to mock it.

Please try it out by running:

.. sourcecode:: bash

  python scripts/scaffold.py


The script uses the `click`-module to assists with autocompletion.

 - Use Tab to auto-complete the first suggest service, or
 - Use the up and down-arrows on the keyboard to select something from the dropdown
 - Press enter to continue

An example interaction:

.. sourcecode:: bash

    $ python scripts/scaffold.py
    Select service: codedeploy

    ==Current Implementation Status==
    [ ] add_tags_to_on_premises_instances
    ...
    [ ] create_deployment
    ...
    [ ] update_deployment_group
    =================================
    Select Operation: create_deployment


        Initializing service	codedeploy
        creating	moto/codedeploy
        creating	moto/codedeploy/models.py
        creating	moto/codedeploy/exceptions.py
        creating	moto/codedeploy/__init__.py
        creating	moto/codedeploy/responses.py
        creating	moto/codedeploy/urls.py
        creating	tests/test_codedeploy
        creating	tests/test_codedeploy/test_server.py
        creating	tests/test_codedeploy/test_codedeploy.py
        inserting code	moto/codedeploy/responses.py
        inserting code	moto/codedeploy/models.py

    Remaining steps after development is complete:
    - Run scripts/implementation_coverage.py,
    - Run scripts/update_backend_index.py.


.. note::  The implementation coverage script is used to automatically update the full list of supported services.

.. warning::  In order to speed up the performance of MotoServer, all AWS URL's that need intercepting are indexed.
              When adding/replacing any URLs in `{service}/urls.py`, please run `python scripts/update_backend_index.py` to update this index.
