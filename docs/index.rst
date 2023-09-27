.. _index:

=============================
Moto: Mock AWS Services
=============================

A library that allows you to easily mock out tests based on
`AWS infrastructure`_.

Getting Started
---------------

If you've never used ``moto`` before, you should read the
:doc:`Getting Started with Moto <docs/getting_started>` guide to get familiar
with ``moto`` and its usage.


Additional Resources
--------------------

* `Moto Source Repository`_
* `Moto Issue Tracker`_

.. _AWS infrastructure: http://aws.amazon.com/
.. _Moto Issue Tracker: https://github.com/getmoto/moto/issues
.. _Moto Source Repository: https://github.com/getmoto/moto

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting Started

   docs/getting_started
   docs/server_mode
   docs/proxy_mode
   docs/faq
   docs/iam
   docs/aws_config
   docs/multi_account

.. toctree::
  :hidden:
  :caption: Configuration

  docs/configuration/index

.. toctree::
  :maxdepth: 1
  :hidden:
  :caption: Implemented Services

  docs/services/index
  docs/services/cf
  docs/services/patching_other_services

.. toctree::
  :maxdepth: 1
  :hidden:
  :caption: Contributing to Moto

  docs/contributing/index
  docs/contributing/installation
  docs/contributing/architecture
  docs/contributing/new_feature
  docs/contributing/checklist
  docs/contributing/faq


.. toctree::
  :maxdepth: 1
  :hidden:
  :titlesonly:
  :caption: Development Tips

  docs/contributing/development_tips/index
  docs/contributing/development_tips/urls
  docs/contributing/development_tips/tests
  docs/contributing/development_tips/utilities
  docs/contributing/development_tips/new_state_transitions
