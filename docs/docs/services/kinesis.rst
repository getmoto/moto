.. _implementedservice_kinesis:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
kinesis
=======



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_kinesis
            def test_kinesis_behaviour:
                boto3.client("kinesis")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] add_tags_to_stream
- [X] create_stream
- [X] decrease_stream_retention_period
- [X] delete_stream
- [ ] deregister_stream_consumer
- [ ] describe_limits
- [X] describe_stream
- [ ] describe_stream_consumer
- [X] describe_stream_summary
- [ ] disable_enhanced_monitoring
- [ ] enable_enhanced_monitoring
- [X] get_records
- [X] get_shard_iterator
- [X] increase_stream_retention_period
- [X] list_shards
- [ ] list_stream_consumers
- [X] list_streams
- [X] list_tags_for_stream
- [X] merge_shards
- [X] put_record
- [X] put_records
- [ ] register_stream_consumer
- [X] remove_tags_from_stream
- [X] split_shard
- [ ] start_stream_encryption
- [ ] stop_stream_encryption
- [ ] subscribe_to_shard
- [ ] update_shard_count

