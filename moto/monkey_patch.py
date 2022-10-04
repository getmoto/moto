from jinja2.environment import Template
from functools import wraps
from xml.dom.minidom import parseString as parseXML
from os import environ as env


MOTO_PRETTIFY_RESPONSES = bool(
    env.get("MOTO_PRETTIFY_RESPONSES", False)
)

original_render = Template.render


@wraps(original_render)
def pretty_render(*args, **kwargs):
    ugly_string = original_render(*args, **kwargs)
    try:
        return parseXML(ugly_string).toprettyxml()
    except Exception:
        return ugly_string


if MOTO_PRETTIFY_RESPONSES:
    Template.render = pretty_render
