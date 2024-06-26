from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from mimetypes import guess_extension
from mimetypes import guess_type
from pathlib import Path
from typing import TYPE_CHECKING

from defusedxml.minidom import parseString
from python_odt_template.markdown_map import transform_map

if TYPE_CHECKING:
    from xml.dom.minidom import Node


class ODTTemplate:
    """An abstraction over an ODT file."""

    def __init__(self, file_path: Path | str):
        self.file_path = file_path
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.unpack()
        self.content = parseString(self.read_file("content.xml"))
        self.styles = parseString(self.read_file("styles.xml"))
        self.manifest = parseString(self.read_file("META-INF/manifest.xml"))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.temp_dir.cleanup()

    def write_file(self, name: str, content: str) -> None:
        with open(self.temp_dir.name + "/" + name, "w") as file:
            file.write(content)

    def read_file(self, name: str) -> str:
        with open(self.temp_dir.name + "/" + name) as file:
            return file.read()

    def add_image(self, filepath: Path, name: str) -> str:
        file_type = guess_type(filepath)
        mimetype = file_type[0] if file_type[0] else ""
        extension = filepath.suffix if filepath.suffix else guess_extension(mimetype)

        media_path = f"Pictures/{name}{extension}"
        shutil.copy(filepath, self.temp_dir.name + "/" + media_path)

        manifests = self.manifest.getElementsByTagName("manifest:manifest")[0]
        media_node = self.manifest.createElement("manifest:file-entry")
        manifests.appendChild(media_node)
        media_node.setAttribute("manifest:full-path", media_path)
        media_node.setAttribute("manifest:media-type", mimetype)
        return media_path

    def unpack(self) -> None:
        with zipfile.ZipFile(self.file_path, "r") as archive:
            archive.extractall(path=self.temp_dir.name)

    def pack(self, target: str | Path) -> None:
        zip_file = io.BytesIO()

        # save any changes made to content.xml, styles.xml and manifest.xml
        self.write_file("content.xml", self.content.toxml())
        self.write_file("styles.xml", self.styles.toxml())
        self.write_file("META-INF/manifest.xml", self.manifest.toxml())

        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipdoc:
            # Add the mimetype file first with no compression
            mimetype_path = os.path.join(self.temp_dir.name, "mimetype")
            if os.path.exists(mimetype_path):
                zipdoc.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

            for root, _, files in os.walk(self.temp_dir.name):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path != mimetype_path:
                        zipdoc.write(
                            file_path,
                            arcname=os.path.relpath(os.path.join(root, file), self.temp_dir.name),
                        )
        Path(target).write_bytes(zip_file.getvalue())

    def get_style_node(self, style_name, styles=None):
        styles = styles or self.get_automatic_styles()
        if not styles:
            return None

        for style in styles.childNodes:
            if hasattr(style, "getAttribute"):
                if style.getAttribute("style:name") == style_name:
                    return style

    def get_office_styles(self) -> Node | None:
        office_styles = self.content.getElementsByTagName("office:styles")
        if not office_styles:
            return None

        return office_styles[0]

    def get_automatic_styles(self) -> Node | None:
        automatic_styles = self.content.getElementsByTagName("office:automatic-styles")
        if not automatic_styles:
            return None

        return automatic_styles[0]

    def insert_style_in_automatic_styles(self, name: str, attrs: dict | None = None, **props):
        attrs = attrs or {}
        auto_styles = self.get_automatic_styles()
        if not auto_styles:
            return

        style = self.content.createElement("style:style")
        style.setAttribute("style:name", name)
        style.setAttribute("style:family", "text")
        style.setAttribute("style:parent-style-name", "Standard")

        for name, value in attrs.items():
            style.setAttribute("style:{}".format(name), value)

        if props:
            style_props = self.content.createElement("style:text-properties")
            for prop, value in props.items():
                style_props.setAttribute(prop, value)

            style.appendChild(style_props)

        return auto_styles.appendChild(style)

    def insert_markdown_style(self, include_code: bool = False, transform_map: dict = transform_map):
        if include_code:
            self.insert_markdown_code_style()

        for transform in transform_map.values():
            if "style" in transform:
                style_name = transform["style"]["name"]
                style = self.get_style_node(style_name)
                if not style:
                    style = self.insert_style_in_automatic_styles(
                        style_name, transform["style"].get("attributes", {}), **transform["style"]["properties"]
                    )

    def insert_markdown_code_style(self):
        # Creates a monospace style to use for <code> tags. This new styles
        # inherits from 'Preformatted_20_Text'.
        preformatted = self.get_style_node("Preformatted_20_Text", self.get_office_styles())
        if not preformatted:
            return

        text_props = preformatted.getElementsByTagName("style:text-properties")[0]
        style_props = {
            "style:font-name": "",
            "fo:font-family": "",
            "style:font-family-generic": "",
            "style:font-pitch": "",
        }

        for style in style_props.keys():
            style_props.update(**{style: text_props.getAttribute(style)})

        self.insert_style_in_automatic_styles("markdown_code", {}, **style_props)
