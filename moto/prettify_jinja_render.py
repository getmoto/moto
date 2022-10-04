from jinja2.environment import Template
from functools import wraps
from xml.dom.minidom import parseString as parseXML
from moto import settings

original_render = Template.render


@wraps(original_render)
def pretty_render(*args, **kwargs):
    ugly_string = original_render(*args, **kwargs)
    try:
        return parseXML(ugly_string).toprettyxml()
    except Exception:
        return ugly_string


if settings.PRETTIFY_RESPONSES:
    Template.render = pretty_render
