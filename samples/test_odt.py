from python_odt_template import ODTTemplateEngine, render_odt
import datetime as dt
from pathlib import Path

sample = Path("simple_template.odt")
output = Path("simple_template_rendered.odt")

document = {
    'datetime': dt.datetime.now(),
    'md_sample': Path('../README.md').read_text()
}

countries = [
    {'country': 'United States', 'capital': 'Washington',
     'cities': ['miami', 'new york', 'california', 'texas', 'atlanta']},
    {'country': 'England', 'capital': 'London', 'cities': ['gales']},
    {'country': 'Japan', 'capital': 'Tokio', 'cities': ['hiroshima', 'nagazaki']},
    {'country': 'Nicaragua', 'capital': 'Managua', 'cities': ['leon', 'granada', 'masaya']},
    {'country': 'Argentina', 'capital': 'Buenos aires'},
    {'country': 'Chile', 'capital': 'Santiago'},
    {'country': 'Mexico', 'capital': 'MExico City', 'cities': ['puebla', 'cancun']},
]

render_odt(sample, output, {'document': document, 'countries': countries})

render_odt("template.odt", "output.odt", {'image': 'writer.png'})
