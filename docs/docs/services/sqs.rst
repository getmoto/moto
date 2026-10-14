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
  
        Calling this method advances the status of the tasks that are returned.
        

- [X] list_queue_tags
- [X] list_queues
- [X] purge_queue
- [X] receive_message
- [X] remove_permission
- [X] send_message
- [X] send_message_batch
- [X] set_queue_attributes
- [X] start_message_move_task
  
        The status of a task progresses according to the state transition model `sqs::messagemovetask`.
        By default, a task completes immediately, so the messages have already been moved when this call returns.

        MaxNumberOfMessagesPerSecond is stored and returned, but does not throttle the move.
        

- [X] tag_queue
- [X] untag_queue

