.. _implementedservice_textract:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
textract
========

.. autoclass:: moto.textract.models.TextractBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] analyze_document
- [ ] analyze_expense
- [ ] analyze_id
- [ ] create_adapter
- [ ] create_adapter_version
- [ ] delete_adapter
- [ ] delete_adapter_version
- [X] detect_document_text
- [ ] get_adapter
- [ ] get_adapter_version
- [X] get_document_analysis
- [X] get_document_text_detection
  
        Pagination has not yet been implemented
        

- [ ] get_expense_analysis
- [ ] get_lending_analysis
- [ ] get_lending_analysis_summary
- [ ] list_adapter_versions
- [ ] list_adapters
- [ ] list_tags_for_resource
- [X] start_document_analysis
  
        The following parameters have not yet been implemented: ClientRequestToken, JobTag, NotificationChannel, OutputConfig, KmsKeyID
        

- [X] start_document_text_detection
  
        The following parameters have not yet been implemented: ClientRequestToken, JobTag, NotificationChannel, OutputConfig, KmsKeyID
        

- [ ] start_expense_analysis
- [ ] start_lending_analysis
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_adapter

