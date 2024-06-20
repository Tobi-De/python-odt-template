from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from pathlib import Path

from django.template import Context
from django.template import Template
from lxml.etree import fromstring
from lxml.etree import tostring
from odfdo import Document
from odfdo import Element

__all__ = ("render_odt",)

logger = logging.getLogger("python_odt_template")


def render_odt(src_file: str | Path, target_file: str | Path, context: dict) -> None:
    # doc = Document.new(Path(src_file))
    # # xml_str = tostring(doc.content.body._Element__element, encoding="unicode")
    # text = doc.content.body.text
    # rendered = Template(template_string=text).render(Context(context))
    # print(rendered)
    # # doc.content.body = Element.from_tag(fromstring(rendered))
    # doc.content.body.text = rendered
    # doc.save(target_file)
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(src_file, "r") as zip_ref:
            zip_ref.extractall(tmpdirname)

        context_xml = Path(tmpdirname) / "content.xml"
        rendered = Template(context_xml.read_text()).render(Context(context))
        print(rendered)
        context_xml.write_text(rendered)

        with zipfile.ZipFile(target_file, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for root, _, files in os.walk(tmpdirname):
                for file in files:
                    file_path = Path(root) / file
                    zip_ref.write(file_path, arcname=file_path.relative_to(tmpdirname))
