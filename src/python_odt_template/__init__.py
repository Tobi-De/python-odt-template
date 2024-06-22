# SPDX-FileCopyrightText: 2024-present Tobi DEGNON <tobidegnon@proton.me>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations
from .libreoffice import libreoffice, convert_to_pdf
from typing import Protocol
from pathlib import Path
from .odtfile import ODTFile
from .jinja import ODTTemplateEngine as JinjaODTTemplateEngine
import logging

__all__ = ("render_odt", "libreoffice", "convert_to_pdf", "ODTTemplateEngine")

logger = logging.getLogger("python_odt_template")

class ODTTemplateEngine(Protocol):

    def render_to_string(self, template: Path, context: dict) -> str:
        pass


def render_odt(
    src_file: str | Path, target_file: str | Path, context: dict, engine: ODTTemplateEngine = None
) -> None:
        odt_file = ODTFile(src_file)
        engine = JinjaODTTemplateEngine(content=odt_file.content, add_media_file=odt_file.add_media_to_archive)
        # Render content.xml keeping just 'office:body' node.
        rendered_content = engine.render_xml(odt_file.content, **context)
        odt_file.content.getElementsByTagName("office:document-content")[0].replaceChild(
            rendered_content.getElementsByTagName("office:body")[0],
            odt_file.content.getElementsByTagName("office:body")[0],
        )

        # Render styles.xml
        odt_file.styles = engine.render_xml(odt_file.styles, **context)

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
