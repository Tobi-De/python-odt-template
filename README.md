# python-odt-template

[![PyPI - Version](https://img.shields.io/pypi/v/python-odt-template.svg)](https://pypi.org/project/python-odt-template)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-odt-template.svg)](https://pypi.org/project/python-odt-template)

-----

> [!IMPORTANT]
> This package currently contains minimal features and is a work-in-progress

## Table of Contents

- [Installation](#installation)
- [License](#license)
- [Credits](#credits)

## Installation

```console
pip install python-odt-template
```

## Usage

```python
from python_odt_template import ODTTemplate
from python_odt_template.jinja import enable_markdown
from python_odt_template.jinja import get_odt_renderer

odt_renderer = get_odt_renderer(media_path="inputs")

with ODTTemplate("inputs/simple_template.odt") as template, enable_markdown(template.get_markdown_filter()):
    odt_renderer.render(
        template,
        context={"document": document, "countries": countries},
    )
    template.pack("simple_template_rendered.odt")
```

## Credits

Thanks to [secretary](https://github.com/christopher-ramirez/secretary) for the enormous amount of integration work on Jinja2 and ODT.

## License

`python-odt-template` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
