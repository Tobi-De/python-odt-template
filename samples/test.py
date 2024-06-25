import datetime as dt
from pathlib import Path

from python_odt_template import ODTTemplate
from python_odt_template.jinja import enable_markdown
from python_odt_template.jinja import get_odt_renderer
from python_odt_template.libreoffice import LibreOffice
from python_odt_template.libreoffice import UnoConvert

odt_renderer = get_odt_renderer(media_path="inputs")
outputs_dir = Path("outputs")
outputs_dir.mkdir(exist_ok=True)

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

with ODTTemplate("inputs/simple_template.odt") as template, enable_markdown(template.markdown_filter):
    odt_renderer.render(
        template,
        context={"document": document, "countries": countries},
    )
    template.pack(outputs_dir / "simple_template_rendered.odt")
    LibreOffice().convert(outputs_dir / "simple_template_rendered.odt", outputs_dir)

with ODTTemplate("inputs/template.odt") as template:
    odt_renderer.render(
        template,
        {"image": "writer.png"},
    )
    template.pack(
        outputs_dir / "template_rendered.odt",
    )
    UnoConvert().convert(outputs_dir / "template_rendered.odt", outputs_dir)
