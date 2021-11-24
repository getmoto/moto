.. _implementedservice_ec2-instance-connect:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

====================
ec2-instance-connect
====================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ec2instanceconnect
            def test_ec2-instance-connect_behaviour:
                boto3.client("ec2-instance-connect")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] send_serial_console_ssh_public_key
- [X] send_ssh_public_key

