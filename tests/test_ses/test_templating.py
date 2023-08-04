from moto.ses.template import parse_template


def test_template_without_args():
    assert parse_template("some template", template_data={}) == "some template"


def test_template_with_simple_arg():
    template = "Dear {{name}},"
    assert parse_template(template, template_data={"name": "John"}) == "Dear John,"


def test_template_with_foreach():
    template = "List:{{#each l}} - {{obj}}{{/each}} and other things"
    kwargs = {"l": [{"obj": "it1"}, {"obj": "it2"}]}
    assert parse_template(template, kwargs) == "List: - it1 - it2 and other things"


def test_template_with_multiple_foreach():
    template = (
        "{{#each l}} - {{obj}}{{/each}} and list 2 {{#each l2}} {{o1}} {{o2}} {{/each}}"
    )
    kwargs = {
        "l": [{"obj": "it1"}, {"obj": "it2"}],
        "l2": [{"o1": "ob1", "o2": "ob2"}, {"o1": "oc1", "o2": "oc2"}],
    }
    assert (
        parse_template(template, kwargs) == " - it1 - it2 and list 2  ob1 ob2  oc1 oc2 "
    )


def test_template_with_single_curly_brace():
    template = "Dear {{name}} my {brace} is fine."
    assert parse_template(template, template_data={"name": "John"}) == (
        "Dear John my {brace} is fine."
    )
