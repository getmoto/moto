from __future__ import unicode_literals
import sure  # noqa

import json

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
    SWFDecisionValidationException,
)
from moto.swf.models import (
    WorkflowType,
)


def test_swf_client_error():
    ex = SWFClientError("ASpecificType", "error message")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "ASpecificType",
        "message": "error message"
    })


def test_swf_unknown_resource_fault():
    ex = SWFUnknownResourceFault("type", "detail")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown type: detail"
    })


def test_swf_unknown_resource_fault_with_only_one_parameter():
    ex = SWFUnknownResourceFault("foo bar baz")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown foo bar baz"
    })


def test_swf_domain_already_exists_fault():
    ex = SWFDomainAlreadyExistsFault("domain-name")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#DomainAlreadyExistsFault",
        "message": "domain-name"
    })


def test_swf_domain_deprecated_fault():
    ex = SWFDomainDeprecatedFault("domain-name")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#DomainDeprecatedFault",
        "message": "domain-name"
    })


def test_swf_serialization_exception():
    ex = SWFSerializationException("value")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#SerializationException",
        "message": "class java.lang.Foo can not be converted to an String  (not a real SWF exception ; happened on: value)"
    })


def test_swf_type_already_exists_fault():
    wft = WorkflowType("wf-name", "wf-version")
    ex = SWFTypeAlreadyExistsFault(wft)

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeAlreadyExistsFault",
        "message": "WorkflowType=[name=wf-name, version=wf-version]"
    })


def test_swf_type_deprecated_fault():
    wft = WorkflowType("wf-name", "wf-version")
    ex = SWFTypeDeprecatedFault(wft)

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeDeprecatedFault",
        "message": "WorkflowType=[name=wf-name, version=wf-version]"
    })


def test_swf_workflow_execution_already_started_fault():
    ex = SWFWorkflowExecutionAlreadyStartedFault()

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#WorkflowExecutionAlreadyStartedFault",
        'message': 'Already Started',
    })


def test_swf_default_undefined_fault():
    ex = SWFDefaultUndefinedFault("execution_start_to_close_timeout")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazonaws.swf.base.model#DefaultUndefinedFault",
        "message": "executionStartToCloseTimeout",
    })


def test_swf_validation_exception():
    ex = SWFValidationException("Invalid token")

    ex.code.should.equal(400)
    json.loads(ex.get_body()).should.equal({
        "__type": "com.amazon.coral.validate#ValidationException",
        "message": "Invalid token",
    })


def test_swf_decision_validation_error():
    ex = SWFDecisionValidationException([
        {"type": "null_value",
         "where": "decisions.1.member.startTimerDecisionAttributes.startToFireTimeout"},
        {"type": "bad_decision_type",
         "value": "FooBar",
         "where": "decisions.1.member.decisionType",
         "possible_values": "Foo, Bar, Baz"},
    ])

    ex.code.should.equal(400)
    ex.error_type.should.equal("com.amazon.coral.validate#ValidationException")

    msg = ex.get_body()
    msg.should.match(r"2 validation errors detected:")
    msg.should.match(
        r"Value null at 'decisions.1.member.startTimerDecisionAttributes.startToFireTimeout' "
        r"failed to satisfy constraint: Member must not be null;"
    )
    msg.should.match(
        r"Value 'FooBar' at 'decisions.1.member.decisionType' failed to satisfy constraint: "
        r"Member must satisfy enum value set: \[Foo, Bar, Baz\]"
    )
