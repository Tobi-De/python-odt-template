from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import zipfile
from mimetypes import guess_extension
from mimetypes import guess_type
from pathlib import Path
from typing import TYPE_CHECKING

from defusedxml.minidom import parseString
from markupsafe import Markup
from python_odt_template.markdown_map import transform_map

if TYPE_CHECKING:
    from xml.dom.minidom import Node, Document


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
            for root, _, files in os.walk(self.temp_dir.name):
                for file in files:
                    zipdoc.write(
                        os.path.join(root, file),
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

    def markdown_filter(self, value: str) -> str:
        """
        Converts markdown value into an ODT formatted text.
        """
        from markdown2 import markdown

        self.insert_markdown_code_style()
        html = markdown(value)
        html_object = parseString("<html>{}</html>".format(html.encode("ascii", "xmlcharrefreplace")))

        # Transform every known HTML tags to odt
        for tagname, transform in transform_map.items():
            html_tags = html_object.getElementsByTagName(tagname)
            for tag in html_tags:
                self.html_tag_to_odt(html_object, tag, transform)

        def _node_to_str(node):
            result = node.toxml()

            # Convert single linebreaks in preformatted nodes to text:line-break
            if node.__class__.__name__ != "Text" and node.getAttribute("text:style-name") == "Preformatted_20_Text":
                result = result.replace("\n", "<text:line-break/>")

            # All double linebreaks should be converted to an empty paragraph
            return result.replace("\n\n", '<text:p text:style-name="Standard"/>')

        str_nodes = (_node_to_str(node) for node in html_object.getElementsByTagName("html")[0].childNodes)
        return Markup("".join(str_nodes))

    def html_tag_to_odt(self, html: Document, tag: Node, transform: dict):
        """
        Replace tag in html with a new odt tag created from the instructions
        in transform dictionary.
        """
        styles_cache = {}
        odt_tag = html.createElement(transform["replace_with"])

        # First lets work with the content
        if tag.hasChildNodes():
            # Only when there's a double linebreak separating list elements,
            # markdown2 wraps the content of the element inside a <p> element.
            # In ODT we should always encapsulate list content in a single paragraph.
            # Here we create the container paragraph in case markdown didn't.
            if tag.localName == "li" and tag.childNodes[0].localName != "p":
                container = html.createElement("text:p")
                odt_tag.appendChild(container)
            elif tag.localName == "code":

                def traverse_preformatted(node):
                    if node.hasChildNodes():
                        for n in node.childNodes:
                            traverse_preformatted(n)
                    else:
                        container = html.createElement("text:span")
                        for text in re.split("(\n)", node.nodeValue.lstrip("\n")):
                            if text == "\n":
                                container.appendChild(html.createElement("text:line-break"))
                            else:
                                container.appendChild(html.createTextNode(text))

                        node.parentNode.replaceChild(container, node)

                traverse_preformatted(tag)
                container = odt_tag
            else:
                container = odt_tag

            # Insert html tag content (actually a group of child nodes)
            for child in tag.childNodes:
                container.appendChild(child.cloneNode(True))

        # Now transform tag attributes
        if "style_attributes" in transform:
            for style, attrs in transform["style_attributes"].items():
                odt_tag.setAttribute("text:{}".format(style), attrs)

        if "attributes" in transform:
            for name, value in transform["attributes"].items():
                odt_tag.setAttribute(name, value)

            # Special handling of <a> tags and their href attribute
            if tag.localName == "a" and tag.hasAttribute("href"):
                odt_tag.setAttribute("xlink:href", tag.getAttribute("href"))

        # Does we need to create a style for displaying this tag?
        if "style" in transform and (not transform["style"]["name"] in styles_cache):
            style_name = transform["style"]["name"]
            style = self.get_style_node(style_name)
            if not style:
                style = self.insert_style_in_automatic_styles(
                    style_name, transform["style"].get("attributes", {}), **transform["style"]["properties"]
                )
                styles_cache[style_name] = style

        tag.parentNode.replaceChild(odt_tag, tag)
