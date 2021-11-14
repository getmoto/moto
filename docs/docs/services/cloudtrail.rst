.. _implementedservice_cloudtrail:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
cloudtrail
==========

Implementation of CloudTrail APIs.

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cloudtrail
            def test_cloudtrail_behaviour:
                boto3.client("cloudtrail")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_tags
- [X] create_trail
- [X] delete_trail
- [X] describe_trails
- [ ] get_event_selectors
- [ ] get_insight_selectors
- [X] get_trail
- [X] get_trail_status
- [ ] list_public_keys
- [ ] list_tags
- [X] list_trails
- [ ] lookup_events
- [ ] put_event_selectors
- [ ] put_insight_selectors
- [ ] remove_tags
- [X] start_logging
- [X] stop_logging
- [ ] update_trail

