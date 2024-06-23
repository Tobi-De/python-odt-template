# SPDX-FileCopyrightText: 2024-present Tobi DEGNON <tobidegnon@proton.me>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from .libreoffice import convert_to_pdf, libreoffice
from .odtfile import ODTFile
from python_odt_template.jinja import get_odt_renderer

__all__ = ("render_odt", "libreoffice", "convert_to_pdf")

logger = logging.getLogger("python_odt_template")


def render_odt(
        src_file: str | Path, target_file: str | Path, context: dict
) -> None:
    odt_file = ODTFile(src_file)
    renderer = get_odt_renderer(content=odt_file.content, media_path=".", media_writer=odt_file.add_image)
    rendered_content = renderer.render_xml(odt_file.content, context)
    odt_file.content.getElementsByTagName("office:document-content")[0].replaceChild(
        rendered_content.getElementsByTagName("office:body")[0],
        odt_file.content.getElementsByTagName("office:body")[0],
    )

    # Render styles.xml
    odt_file.styles = renderer.render_xml(odt_file.styles, context)

    logger.debug("Template rendering finished")

    odt_file.files["content.xml"] = odt_file.content.toxml().encode(
        "ascii", "xmlcharrefreplace"
    )
    odt_file.files["styles.xml"] = odt_file.styles.toxml().encode(
        "ascii", "xmlcharrefreplace"
    )
    odt_file.files["META-INF/manifest.xml"] = odt_file.manifest.toxml().encode(
        "ascii", "xmlcharrefreplace"
    )

    document = odt_file.pack_document(odt_file.files)
    Path(target_file).write_bytes(document.getvalue())
