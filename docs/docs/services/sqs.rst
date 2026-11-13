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
- [X] cancel_message_move_task
  
        Only RUNNING tasks can be cancelled. Message move tasks complete as soon as they are created, so cancelling an existing task always raises an UnsupportedOperation error.
        

- [X] change_message_visibility
- [X] change_message_visibility_batch
- [X] create_queue
- [X] delete_message
- [X] delete_message_batch
- [X] delete_queue
- [X] get_queue_attributes
- [X] get_queue_url
- [X] list_dead_letter_source_queues
- [X] list_message_move_tasks
- [X] list_queue_tags
- [X] list_queues
- [X] purge_queue
- [X] receive_message
- [X] remove_permission
- [X] send_message
- [X] send_message_batch
- [X] set_queue_attributes
- [X] start_message_move_task
  
        The messages are moved immediately, so the task is COMPLETED as soon as it is created.

        Without a DestinationArn, each message is moved back to the queue it was moved to the dead-letter queue from. Messages that did not get there through a redrive policy are moved to the source queue if the dead-letter queue has exactly one, and are left in place otherwise.
        

- [X] tag_queue
- [X] untag_queue

