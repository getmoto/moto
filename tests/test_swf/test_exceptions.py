from __future__ import unicode_literals

from moto.swf.exceptions import (
    SWFClientError,
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
    SWFSerializationException,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
    SWFWorkflowExecutionAlreadyStartedFault,
    SWFDefaultUndefinedFault,
    SWFValidationException,
)
from moto.swf.models import (
    WorkflowType,
)

def test_swf_client_error():
    ex = SWFClientError("error message", "ASpecificType")

    ex.status.should.equal(400)
    ex.error_code.should.equal("ASpecificType")
    ex.body.should.equal({
        "__type": "ASpecificType",
        "message": "error message"
    })

def test_swf_unknown_resource_fault():
    ex = SWFUnknownResourceFault("type", "detail")

    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown type: detail"
    })

def test_swf_unknown_resource_fault_with_only_one_parameter():
    ex = SWFUnknownResourceFault("foo bar baz")

    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown foo bar baz"
    })

def test_swf_domain_already_exists_fault():
    ex = SWFDomainAlreadyExistsFault("domain-name")

    ex.status.should.equal(400)
    ex.error_code.should.equal("DomainAlreadyExistsFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#DomainAlreadyExistsFault",
        "message": "domain-name"
    })

def test_swf_domain_deprecated_fault():
    ex = SWFDomainDeprecatedFault("domain-name")

    ex.status.should.equal(400)
    ex.error_code.should.equal("DomainDeprecatedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#DomainDeprecatedFault",
        "message": "domain-name"
    })

def test_swf_serialization_exception():
    ex = SWFSerializationException("value")

    ex.status.should.equal(400)
    ex.error_code.should.equal("SerializationException")
    ex.body["__type"].should.equal("com.amazonaws.swf.base.model#SerializationException")
    ex.body["Message"].should.match(r"class java.lang.Foo can not be converted to an String")

def test_swf_type_already_exists_fault():
    wft = WorkflowType("wf-name", "wf-version")
    ex = SWFTypeAlreadyExistsFault(wft)

    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeAlreadyExistsFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeAlreadyExistsFault",
        "message": "WorkflowType=[name=wf-name, version=wf-version]"
    })

def test_swf_type_deprecated_fault():
    wft = WorkflowType("wf-name", "wf-version")
    ex = SWFTypeDeprecatedFault(wft)

    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeDeprecatedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeDeprecatedFault",
        "message": "WorkflowType=[name=wf-name, version=wf-version]"
    })

def test_swf_workflow_execution_already_started_fault():
    ex = SWFWorkflowExecutionAlreadyStartedFault()

    ex.status.should.equal(400)
    ex.error_code.should.equal("WorkflowExecutionAlreadyStartedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#WorkflowExecutionAlreadyStartedFault",
    })

def test_swf_default_undefined_fault():
    ex = SWFDefaultUndefinedFault("execution_start_to_close_timeout")

    ex.status.should.equal(400)
    ex.error_code.should.equal("DefaultUndefinedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#DefaultUndefinedFault",
        "message": "executionStartToCloseTimeout",
    })

def test_swf_validation_exception():
    ex = SWFValidationException("Invalid token")

    ex.status.should.equal(400)
    ex.error_code.should.equal("ValidationException")
    ex.body.should.equal({
        "__type": "com.amazon.coral.validate#ValidationException",
        "message": "Invalid token",
    })
