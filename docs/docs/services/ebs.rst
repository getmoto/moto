.. _implementedservice_ebs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ebs
===

.. autoclass:: moto.ebs.models.EBSBackend

|start-h3| Implemented features for this service |end-h3|

- [X] complete_snapshot
  
        The following parameters are not yet supported: ChangedBlocksCount, Checksum, ChecksumAlgorithm, ChecksumAggregationMethod
        

- [X] get_snapshot_block
  
        The BlockToken-parameter is not yet implemented
        

- [X] list_changed_blocks
  
        The following parameters are not yet implemented: NextToken, MaxResults, StartingBlockIndex
        

- [X] list_snapshot_blocks
  
        The following parameters are not yet implemented: NextToken, MaxResults, StartingBlockIndex
        

- [X] put_snapshot_block
  
        The following parameters are currently not taken into account: DataLength, Progress.
        The Checksum and ChecksumAlgorithm are taken at face-value, but no validation takes place.
        

- [X] start_snapshot
  
        The following parameters are not yet implemented: ParentSnapshotId, ClientToken, Encrypted, KmsKeyArn, Timeout
        


