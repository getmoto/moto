.. _implementedservice_sqs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
sqs
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_sqs
            def test_sqs_behaviour:
                boto3.client("sqs")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] add_permission
- [X] change_message_visibility
- [ ] change_message_visibility_batch
- [X] create_queue
- [X] delete_message
- [ ] delete_message_batch
- [X] delete_queue
- [X] get_queue_attributes
- [X] get_queue_url
- [X] list_dead_letter_source_queues
- [X] list_queue_tags
- [X] list_queues
- [X] purge_queue
- [X] receive_message
- [X] remove_permission
- [X] send_message
- [X] send_message_batch
- [X] set_queue_attributes
- [X] tag_queue
- [X] untag_queue

