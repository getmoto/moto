.. _implementedservice_firehose:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
firehose
========

.. autoclass:: moto.firehose.models.FirehoseBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_firehose
            def test_firehose_behaviour:
                boto3.client("firehose")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_delivery_stream
  Create a Kinesis Data Firehose delivery stream.

- [X] delete_delivery_stream
  Delete a delivery stream and its data.

        AllowForceDelete option is ignored as we only superficially
        apply state.
        

- [X] describe_delivery_stream
  Return description of specified delivery stream and its status.

        Note:  the 'limit' and 'exclusive_start_destination_id' parameters
        are not currently processed/implemented.
        

- [X] list_delivery_streams
  Return list of delivery streams in alphabetic order of names.

- [X] list_tags_for_delivery_stream
  Return list of tags.

- [X] put_record
  Write a single data record into a Kinesis Data firehose stream.

- [X] put_record_batch
  Write multiple data records into a Kinesis Data firehose stream.

- [ ] start_delivery_stream_encryption
- [ ] stop_delivery_stream_encryption
- [X] tag_delivery_stream
  Add/update tags for specified delivery stream.

- [X] untag_delivery_stream
  Removes tags from specified delivery stream.

- [X] update_destination
  Updates specified destination of specified delivery stream.


