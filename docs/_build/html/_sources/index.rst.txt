.. _index:

=============================
Moto: A Mock library for boto
=============================

A library that allows you to easily mock out tests based on
_`AWS infrastructure`.

.. _AWS infrastructure: http://aws.amazon.com/

Getting Started
---------------

If you've never used ``moto`` before, you should read the
:doc:`Getting Started with Moto <getting_started>` guide to get familiar
with ``moto`` & its usage.

Currently implemented Services
------------------------------

* **Compute**

  * :doc:`Elastic Compute Cloud <ec2_tut>`
  * AMI
  * EBS
  * Instances
  * Security groups
  * Tags
  * Auto Scaling

* **Storage and content delivery**

  * S3
  * Glacier

* **Database**
  
  * RDS
  * DynamoDB
  * Redshift

* **Networking**
  
  * Route53

* **Administration and security**

  * Identity & access management
  * CloudWatch

* **Deployment and management**

  * CloudFormation

* **Analytics**

  * Kinesis
  * EMR

* **Application service**

  * SQS
  * SES

* **Mobile services**

  * SNS

Additional Resources
--------------------

* `Moto Source Repository`_
* `Moto Issue Tracker`_

.. _Moto Issue Tracker: https://github.com/spulec/moto/issues
.. _Moto Source Repository: https://github.com/spulec/moto

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. toctree::
   :maxdepth: 2
   :hidden:
   :glob:

   getting_started
