.. _implementedservice_polly:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
polly
=====

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_polly
            def test_polly_behaviour:
                boto3.client("polly")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] delete_lexicon
- [X] describe_voices
- [X] get_lexicon
- [ ] get_speech_synthesis_task
- [X] list_lexicons
- [ ] list_speech_synthesis_tasks
- [X] put_lexicon
- [ ] start_speech_synthesis_task
- [ ] synthesize_speech

