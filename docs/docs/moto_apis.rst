.. _moto_apis:

=========
Moto APIs
=========

Moto provides some internal APIs to view and change the state of the backends.

Reset API
---------

This API resets the state of all of the backends. Send an HTTP POST to reset::

   requests.post("http://motoapi.amazonaws.com/moto-api/reset")

Dashboard
---------

Moto comes with a dashboard to view the current state of the system::

    http://localhost:5000/moto-api/
