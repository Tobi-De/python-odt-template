import datetime as dt
from pathlib import Path

from python_odt_template import ODTTemplate
from python_odt_template.jinja import enable_markdown
from python_odt_template.jinja import get_odt_renderer
from python_odt_template.libreoffice import convert_to_pdf

odt_renderer = get_odt_renderer(media_path="inputs")

document = {
    "datetime": dt.datetime.now(),
    "md_sample": Path("../README.md").read_text(),
}

countries = [
    {
        "country": "United States",
        "capital": "Washington",
        "cities": ["miami", "new york", "california", "texas", "atlanta"],
    },
    {"country": "England", "capital": "London", "cities": ["gales"]},
    {"country": "Japan", "capital": "Tokio", "cities": ["hiroshima", "nagazaki"]},
    {
        "country": "Nicaragua",
        "capital": "Managua",
        "cities": ["leon", "granada", "masaya"],
    },
    {"country": "Argentina", "capital": "Buenos aires"},
    {"country": "Chile", "capital": "Santiago"},
    {"country": "Mexico", "capital": "MExico City", "cities": ["puebla", "cancun"]},
]

with ODTTemplate("inputs/simple_template.odt") as template, enable_markdown(template.get_markdown_filter()):
    odt_renderer.render(
        template,
        context={"document": document, "countries": countries},
    )
    template.pack("simple_template_rendered.odt")

with ODTTemplate("inputs/template.odt") as template:
    odt_renderer.render(
        template,
        {"image": "writer.png"},
    )
    template.pack(
        "template_rendered.odt",
    )
    convert_to_pdf("template_rendered.odt", "outputs")

with ODTTemplate("inputs/checkin.odt") as template:
    odt_renderer.render(template, {"value": "Something"})
    template.pack("checkin_rendered.odt")
    convert_to_pdf("checkin_rendered.odt", "outputs")
