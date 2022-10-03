from jinja2.environment import Template
import typing as t
import os


def render(self, *args: t.Any, **kwargs: t.Any) -> str:
    """This method accepts the same arguments as the `dict` constructor:
    A dict, a dict subclass or some keyword arguments.  If no arguments
    are given the context will be empty.  These two calls do the same::

        template.render(knights='that say nih')
        template.render({'knights': 'that say nih'})

    This will return the rendered template as a string.
    """
    import xml.dom.minidom
    if self.environment.is_async:
        import asyncio

        close = False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            close = True

        try:
            return loop.run_until_complete(self.render_async(*args, **kwargs))
        finally:
            if close:
                loop.close()

    ctx = self.new_context(dict(*args, **kwargs))
    MOTO_PRETTIFY_RESPONSES = bool(
        os.environ.get("MOTO_PRETTIFY_RESPONSES", False)
    )
    try:
        ugly_string = self.environment.concat(self.root_render_func(ctx))
        if MOTO_PRETTIFY_RESPONSES:
            try:
                dom = xml.dom.minidom.parseString(ugly_string)
            except Exception:
                return ugly_string
            pretty_xml_as_string = dom.toprettyxml()
            return pretty_xml_as_string
        else:
            return ugly_string
    except Exception:
        self.environment.handle_exception()


Template.render = render
