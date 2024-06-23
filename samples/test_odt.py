import datetime as dt
from pathlib import Path

from python_odt_template import render_odt


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

render_odt(
    "inputs/simple_template.odt",
    "simple_template_rendered.odt",
    {"document": document, "countries": countries},
)

render_odt(
    "inputs/template.odt", "template_rendered.odt", {"image": "inputs/writer.png", "image2": "inputs/writer.png"}
)

render_odt("inputs/checkin.odt", "checkin_rendered.odt", {"value": "Something"})
