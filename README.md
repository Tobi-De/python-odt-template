# python-odt-template

[![PyPI - Version](https://img.shields.io/pypi/v/python-odt-template.svg)](https://pypi.org/project/python-odt-template)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-odt-template.svg)](https://pypi.org/project/python-odt-template)

-----

> [!IMPORTANT]
> This package currently contains minimal features and is a work-in-progress

## Table of Contents

- [python-odt-template](#python-odt-template)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Jinja2](#jinja2)
    - [Django](#django)
  - [Alternatives](#alternatives)
  - [Credits](#credits)
  - [License](#license)

## Installation

```console
pip install python-odt-template
```

## Usage

### Jinja2

```python
from python_odt_template import ODTTemplate
from python_odt_template.jinja import enable_markdown
from python_odt_template.jinja import get_odt_renderer
from python_odt_template.libreoffice import convert_to_pdf

odt_renderer = get_odt_renderer(media_path="inputs")

with ODTTemplate("inputs/simple_template.odt") as template:
    odt_renderer.render(
        template,
        context={"document": document, "countries": countries},
    )
    template.pack("simple_template_rendered.odt")
    convert_to_pdf("simple_template_rendered.odt", "outputs")
```

### Django

```python
# settings.py

# Add at least one staticfiles dirs, this is what the imgae filter will use to find images
STATICFILES_DIRS = [BASE_DIR / "example" / "static"]

# Add the image filter to the builtins templates config
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        ...
        "OPTIONS": {
           ...
            "builtins": ["python_odt_template.django"],
        },
    },
]


# views.py
from python_odt_template import ODTTemplate
from python_odt_template.django import get_odt_renderer
from python_odt_template.libreoffice import convert_to_pdf


odt_renderer = get_odt_renderer()


def render_odt(request):
    with ODTTemplate("template.odt") as template:
        odt_renderer.render(
            template,
            {"image": "writer.png"},
        )
        template.pack("template_rendered.odt")
        convert_to_pdf("template_rendered.odt", "outputs")
    return FileResponse(
        open("outputs/template_rendered.pdf", "rb"), as_attachment=True, filename="template_rendered.pdf"
    )
```

## Alternatives

- [python-docx-template](https://github.com/elapouya/python-docx-template)

## Credits

Thanks to [secretary](https://github.com/christopher-ramirez/secretary) for the enormous amount of integration work on Jinja2 and ODT.

## License

`python-odt-template` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
