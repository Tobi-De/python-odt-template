# python-odt-template

[![PyPI - Version](https://img.shields.io/pypi/v/python-odt-template.svg)](https://pypi.org/project/python-odt-template)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-odt-template.svg)](https://pypi.org/project/python-odt-template)

-----

> [!IMPORTANT]
> This package currently contains minimal features and is a work-in-progress

Render ODT files using Jinja2 or the Django templates Language, with support for converting documents to PDF via the LibreOffice CLI. 

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

`python-odt-template` supports basic tags and control flow from Django or Jinja2, enabling variable printing and simple logic. However, advanced features like `extends`, `include`, and `block` are not supported. Directly mixing tags with text may lead to invalid ODT templates. Instead, we recommend using LibreOffice Writer's visual fields for dynamic content insertion. To do this, navigate to Insert > Fields > Other... (or press Ctrl+F2), select the Functions tab, choose Input field, and insert your code in the dialog that appears. This method supports simple control flow for dynamic content.

Additionally, `python-odt-template` introduces an `image` tag for both Jinja2 and Django, allowing image insertion by replacing a placeholder image in your document. Use the tag (e.g., `{{ company_logo|image }}`) and provide the corresponding image path in the context (`company_logo`). For Django, the image path is resolved using the first entry in `STATICFILES_DIRS`. For Jinja2, specify a `media_path` when creating the renderer to set the base path for images.

> [!NOTE]
> For now, you can get more detailed information at the Secretary project's readme at https://github.com/christopher-ramirez/secretary.


### Jinja2

```python
from python_odt_template import ODTTemplate
from python_odt_template.jinja import enable_markdown
from python_odt_template.jinja import get_odt_renderer
from python_odt_template.libreoffice import libreoffice

odt_renderer = get_odt_renderer(media_path="inputs")

with ODTTemplate("inputs/simple_template.odt") as template:
    odt_renderer.render(
        template,
        context={"document": document, "countries": countries},
    )
    template.pack("simple_template_rendered.odt")
    libreoffice.convert("simple_template_rendered.odt", "outputs")
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
        libreoffice.convert("template_rendered.odt", "outputs")
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
