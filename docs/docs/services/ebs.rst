.. _implementedservice_ebs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ebs
===

.. autoclass:: moto.ebs.models.EBSBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ebs
            def test_ebs_behaviour:
                boto3.client("ebs")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] complete_snapshot
- [X] get_snapshot_block
  
        The BlockToken-parameter is not yet implemented
        

- [X] list_changed_blocks
  
        The following parameters are not yet implemented: NextToken, MaxResults, StartingBlockIndex
        

- [X] list_snapshot_blocks
- [X] put_snapshot_block
- [X] start_snapshot

