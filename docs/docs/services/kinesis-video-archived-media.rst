.. _implementedservice_kinesis-video-archived-media:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============================
kinesis-video-archived-media
============================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_kinesisvideoarchivedmedia
            def test_kinesisvideoarchivedmedia_behaviour:
                boto3.client("kinesis-video-archived-media")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] get_clip
- [X] get_dash_streaming_session_url
- [X] get_hls_streaming_session_url
- [ ] get_images
- [ ] get_media_for_fragment_list
- [ ] list_fragments

