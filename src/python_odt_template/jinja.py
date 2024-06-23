from pathlib import Path

from jinja2 import Environment, Undefined
from markupsafe import Markup

from python_odt_template.filters import finalize_value, pad_string
from python_odt_template.renderer import ODTRenderer


class UndefinedSilently(Undefined):
    # Silently undefined,
    # see http://stackoverflow.com/questions/6182498
    def silently_undefined(*args, **kwargs):
        return ""

    return_new = lambda *args, **kwargs: UndefinedSilently()

    __unicode__ = silently_undefined
    __str__ = silently_undefined
    __call__ = return_new
    __getattr__ = return_new


environment = Environment(
    undefined=UndefinedSilently,
    autoescape=True,
    finalize=finalize_value,
)


def get_odt_renderer(media_path: str | Path, env: Environment = environment):
    media_path = Path(media_path)

    def image_filter(value):
        return media_path / value

    def render(template_str, context):
        return env.from_string(template_str).render(context)

    env.filters["pad"] = pad_string
    env.globals["SafeValue"] = Markup
    env.filters["image"] = image_filter
    odt_renderer = ODTRenderer(
        block_end_string=env.block_end_string,
        block_start_string=env.block_start_string,
        variable_end_string=env.variable_end_string,
        variable_start_string=env.variable_start_string,
        render_func=render,
    )
    return odt_renderer
