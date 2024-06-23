import datetime as dt
from pathlib import Path

from python_odt_template import ODTFile
from python_odt_template.jinja import get_odt_renderer, environment

odt_renderer = get_odt_renderer("inputs")

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

odt_file = ODTFile("inputs/simple_template.odt")
environment.filters["markdown"] = odt_file.get_markdown_filter()
odt_renderer.render(
    src_file=odt_file,
    target_file="simple_template_rendered.odt",
    context={"document": document, "countries": countries},
)

environment.filters.pop("markdown")
odt_renderer.render(
    ODTFile("inputs/template.odt"),
    "template_rendered.odt",
    {"image": "writer.png"},
)

odt_renderer.render(
    ODTFile("inputs/checkin.odt"), "checkin_rendered.odt", {"value": "Something"}
)
