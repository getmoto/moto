.. _implementedservice_sqs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
sqs
===

|start-h3| Implemented features for this service |end-h3|

- [X] add_permission
- [ ] cancel_message_move_task
- [X] change_message_visibility
- [X] change_message_visibility_batch
- [X] create_queue
- [X] delete_message
- [X] delete_message_batch
- [X] delete_queue
- [X] get_queue_attributes
- [X] get_queue_url
- [X] list_dead_letter_source_queues
- [ ] list_message_move_tasks
- [X] list_queue_tags
- [X] list_queues
- [X] purge_queue
- [X] receive_message
- [X] remove_permission
- [X] send_message
- [X] send_message_batch
- [X] set_queue_attributes
- [ ] start_message_move_task
- [X] tag_queue
- [X] untag_queue


|start-h3| Configuration |end-h3|

CRC32 Header Generation
^^^^^^^^^^^^^^^^^^^^^^^^

By default, Moto generates CRC32 checksums for SQS responses and includes them in the ``x-amz-crc32`` header.

However, some SDK versions (such as the .NET AWS SDK v4) may have compatibility issues with CRC32 validation. To disable CRC32 header generation for SQS responses, set:

.. code-block:: bash

    MOTO_SQS_DISABLE_CRC32_VALIDATION=true

When disabled, the ``x-amz-crc32`` header will not be included in SQS responses.

