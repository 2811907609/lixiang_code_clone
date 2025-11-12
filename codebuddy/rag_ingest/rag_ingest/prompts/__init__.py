import os

from jinja2 import Environment, FileSystemLoader

_current_dir = os.path.dirname(os.path.abspath(__file__))
_template_dir = os.path.join(_current_dir, 'templates')

_environment = Environment(loader=FileSystemLoader(_template_dir))


def render(name, **kwargs):
    template = _environment.get_template(name)
    return template.render(**kwargs)
