from moto.ses.template import parse_template
import sure  # noqa # pylint: disable=unused-import


def test_template_without_args():
    parse_template("some template", template_data={}).should.equal("some template")


def test_template_with_simple_arg():
    t = "Dear {{name}},"
    parse_template(t, template_data={"name": "John"}).should.equal("Dear John,")


def test_template_with_foreach():
    t = "List:{{#each l}} - {{obj}}{{/each}} and other things"
    kwargs = {"l": [{"obj": "it1"}, {"obj": "it2"}]}
    parse_template(t, kwargs).should.equal("List: - it1 - it2 and other things")


def test_template_with_multiple_foreach():
    t = "{{#each l}} - {{obj}}{{/each}} and list 2 {{#each l2}} {{o1}} {{o2}} {{/each}}"
    kwargs = {
        "l": [{"obj": "it1"}, {"obj": "it2"}],
        "l2": [{"o1": "ob1", "o2": "ob2"}, {"o1": "oc1", "o2": "oc2"}],
    }
    parse_template(t, kwargs).should.equal(" - it1 - it2 and list 2  ob1 ob2  oc1 oc2 ")


def test_template_with_single_curly_brace():
    t = "Dear {{name}} my {brace} is fine."
    parse_template(t, template_data={"name": "John"}).should.equal(
        "Dear John my {brace} is fine."
    )
