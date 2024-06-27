from __future__ import annotations

import re
from typing import TYPE_CHECKING

from defusedxml.minidom import parseString
from markupsafe import Markup
from python_odt_template.markdown_map import transform_map

if TYPE_CHECKING:
    from xml.dom.minidom import Node, Document


def pad_string(value, length=5):
    value = str(value)
    return value.zfill(length)


def odt_markdown(value: str) -> str:
    """
    Converts markdown value into an ODT formatted text.
    """
    from markdown2 import markdown

    html = markdown(value)
    html_object = parseString("<html>{}</html>".format(html.encode("ascii", "xmlcharrefreplace")))

    # Transform every known HTML tags to odt
    for tagname, transform in transform_map.items():
        html_tags = html_object.getElementsByTagName(tagname)
        for tag in html_tags:
            _html_tag_to_odt(html_object, tag, transform)

    str_nodes = (node.toxml() for node in html_object.getElementsByTagName("html")[0].childNodes)
    return Markup("".join(str_nodes))


def _html_tag_to_odt(html: Document, tag: Node, transform: dict):
    """
    Replace tag in html with a new odt tag created from the instructions
    in transform dictionary.
    """
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

    tag.parentNode.replaceChild(odt_tag, tag)
