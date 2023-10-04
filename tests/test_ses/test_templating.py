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


def test_template_with_if():
    template = "Dear {{ #if name }}John{{ /if }}"
    assert parse_template(template, template_data={"name": True}) == "Dear John"
    assert parse_template(template, template_data={"name": False}) == "Dear "


def test_template_with_if_else():
    template = "Dear {{ #if name }}John{{ else }}English{{ /if }}"
    assert parse_template(template, template_data={"name": True}) == "Dear John"
    assert parse_template(template, template_data={"name": False}) == "Dear English"


def test_template_with_nested_foreaches():
    template = (
        "{{#each l}} - {{obj}} {{#each l2}} {{o1}} {{/each}} infix-each {{/each}}"
    )
    kwargs = {
        "name": True,
        "l": [
            {
                "obj": "it1",
                "l2": [{"o1": "ob1", "o2": "ob2"}, {"o1": "oc1", "o2": "oc2"}],
            },
            {"obj": "it2", "l2": [{"o1": "ob3"}]},
        ],
    }
    assert (
        parse_template(template, kwargs)
        == " - it1  ob1  oc1  infix-each  - it2  ob3  infix-each "
    )


def test_template_with_nested_ifs_and_foreaches():
    template = "{{#each l}} - {{obj}} {{#if name}} post-if {{#each l2}} {{o1}} {{/each}} pre-if-end {{else}}elsedata{{/if}} post-if {{/each}}"
    kwargs = {
        "name": True,
        "l": [
            {"obj": "it1", "name": True, "l2": [{"o1": "ob1"}]},
            {"obj": "it2", "name": False},
        ],
    }
    assert (
        parse_template(template, kwargs)
        == " - it1  post-if  ob1  pre-if-end  post-if  - it2 elsedata post-if "
    )
