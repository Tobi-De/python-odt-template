from pathlib import Path
from typing import Callable

from xml.dom.minidom import Document

from jinja2 import Environment, Undefined
from markupsafe import Markup

from python_odt_template.filters import finalize_value, get_markdown_filter, pad_string

from python_odt_template.renderer import ODTRenderer


def get_image_filter(media_path: str | Path) -> Callable[[str], str]:
    media_path = Path(media_path)

    def image_filter(value):
        return media_path / value

    return image_filter


def get_odt_renderer(content: Document, media_path: str, media_writer):
    environment = Environment(
        undefined=UndefinedSilently,
        autoescape=True,
        finalize=finalize_value,
    )

    def render(template_str, context):
        return environment.from_string(template_str).render(context)

    environment.filters["pad"] = pad_string
    environment.globals["SafeValue"] = Markup
    environment.filters["markdown"] = get_markdown_filter(content)
    environment.filters["image"] = get_image_filter(media_path)
    odt_renderer = ODTRenderer(
        block_end_string=environment.block_end_string,
        block_start_string=environment.block_start_string,
        variable_end_string=environment.variable_end_string,
        variable_start_string=environment.variable_start_string,
        media_writer=media_writer,
        render_func=render,
    )
    return odt_renderer


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
