from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from jinja2 import Environment
from jinja2 import Undefined
from markupsafe import Markup
from python_odt_template.renderer import ODTRenderer

__all__ = ("get_odt_renderer", "enable_markdown")


class UndefinedSilently(Undefined):
    # Silently undefined,
    # see http://stackoverflow.com/questions/6182498
    def silently_undefined(*_, **__):
        return ""

    def return_new(*_, **__):
        return UndefinedSilently()

    __unicode__ = silently_undefined
    __str__ = silently_undefined
    __call__ = return_new
    __getattr__ = return_new


def finalize_value(value):
    """Escapes variables values."""
    if isinstance(value, Markup):
        return value

    """
        Encodes XML reserved chars in value (eg. &, <, >) and also replaces
        the control chars \n and \t control chars to their ODF counterparts.
        """
    value = Markup.escape(value)
    return Markup(
        value.replace("\n", Markup("<text:line-break/>"))
        .replace("\t", Markup("<text:tab/>"))
        .replace("\x0b", "<text:space/>")
        .replace("\x0c", "<text:space/>")
    )


environment = Environment(
    undefined=UndefinedSilently,
    autoescape=True,
    finalize=finalize_value,
)


def get_odt_renderer(media_path: str | Path, env: Environment = environment) -> ODTRenderer:
    media_path = Path(media_path)

    def image_filter(value):
        return media_path / value

    def render(template_str: str, context: dict) -> str:
        return env.from_string(template_str).render(context)

    env.filters["pad"] = pad_string
    env.globals["SafeValue"] = Markup
    env.filters["image"] = image_filter
    return ODTRenderer(
        block_end_string=env.block_end_string,
        block_start_string=env.block_start_string,
        variable_end_string=env.variable_end_string,
        variable_start_string=env.variable_start_string,
        render_func=render,
    )


@contextmanager
def enable_markdown(markdown_filter: callable, env: Environment = environment):
    try:
        env.filters["markdown"] = markdown_filter
        yield
    finally:
        env.filters.pop("markdown")


def pad_string(value, length=5):
    value = str(value)
    return value.zfill(length)
