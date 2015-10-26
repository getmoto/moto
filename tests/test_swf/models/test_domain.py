from sure import expect

from moto.swf.models import Domain


def test_domain_short_dict_representation():
    domain = Domain("foo", "52")
    domain.to_short_dict().should.equal({"name":"foo", "status":"REGISTERED"})

    domain.description = "foo bar"
    domain.to_short_dict()["description"].should.equal("foo bar")

def test_domain_full_dict_representation():
    domain = Domain("foo", "52")

    domain.to_full_dict()["domainInfo"].should.equal(domain.to_short_dict())
    _config = domain.to_full_dict()["configuration"]
    _config["workflowExecutionRetentionPeriodInDays"].should.equal("52")

def test_domain_string_representation():
    domain = Domain("my-domain", "60")
    str(domain).should.equal("Domain(name: my-domain, status: REGISTERED)")

def test_domain_add_to_activity_task_list():
    domain = Domain("my-domain", "60")
    domain.add_to_activity_task_list("foo", "bar")
    domain.activity_task_lists.should.equal({
        "foo": ["bar"]
    })

def test_domain_activity_tasks():
    domain = Domain("my-domain", "60")
    domain.add_to_activity_task_list("foo", "bar")
    domain.add_to_activity_task_list("other", "baz")
    domain.activity_tasks.should.equal(["bar", "baz"])

def test_domain_add_to_decision_task_list():
    domain = Domain("my-domain", "60")
    domain.add_to_decision_task_list("foo", "bar")
    domain.decision_task_lists.should.equal({
        "foo": ["bar"]
    })

def test_domain_decision_tasks():
    domain = Domain("my-domain", "60")
    domain.add_to_decision_task_list("foo", "bar")
    domain.add_to_decision_task_list("other", "baz")
    domain.decision_tasks.should.equal(["bar", "baz"])
