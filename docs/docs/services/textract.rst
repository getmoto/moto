.. _implementedservice_textract:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
textract
========

.. autoclass:: moto.textract.models.TextractBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_textract
            def test_textract_behaviour:
                boto3.client("textract")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] analyze_document
- [ ] analyze_expense
- [ ] analyze_id
- [ ] detect_document_text
- [ ] get_document_analysis
- [X] get_document_text_detection
- [ ] get_expense_analysis
- [ ] start_document_analysis
- [X] start_document_text_detection
- [ ] start_expense_analysis

