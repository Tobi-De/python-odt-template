from pathlib import Path

from python_odt_template import ODTTemplate
from python_odt_template.django import get_odt_renderer
from python_odt_template.libreoffice import convert_to_pdf

from django.contrib import admin
from django.http import FileResponse
from django.urls import path

outputs_dir = Path("../samples/outputs")
outputs_dir.mkdir(exist_ok=True)
inputs_dir = Path("../samples/inputs")


odt_renderer = get_odt_renderer()


def render_odt(_):
    with ODTTemplate(inputs_dir / "template.odt") as template:
        odt_renderer.render(
            template,
            {"image": "writer.png"},
        )
        template.pack(
            outputs_dir / "template_rendered.odt",
        )
        convert_to_pdf(outputs_dir / "template_rendered.odt", outputs_dir)
    return FileResponse(
        open(outputs_dir / "template_rendered.pdf", "rb"), as_attachment=True, filename="template_rendered.pdf"
    )


urlpatterns = [
    path("", render_odt),
    path("admin/", admin.site.urls),
]
