from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from typing import TYPE_CHECKING
from urllib.parse import unquote
from xml.parsers.expat import ExpatError

from defusedxml.minidom import parseString
from markupsafe import Markup

if TYPE_CHECKING:
    from python_odt_template import ODTTemplate
    from xml.dom.minidom import Document
    from xml.dom.minidom import Node

logger = logging.getLogger("python_odt_template")

FLOW_REFERENCES = {
    "text:p": "text:p",
    "paragraph": "text:p",
    "before::paragraph": "text:p",
    "after::paragraph": "text:p",
    "table:table-row": "table:table-row",
    "table-row": "table:table-row",
    "row": "table:table-row",
    "before::table-row": "table:table-row",
    "after::table-row": "table:table-row",
    "before::row": "table:table-row",
    "after::row": "table:table-row",
    "table:table-cell": "table:table-cell",
    "table-cell": "table:table-cell",
    "cell": "table:table-cell",
    "before::table-cell": "table:table-cell",
    "after::table-cell": "table:table-cell",
    "before::cell": "table:table-cell",
    "after::cell": "table:table-cell",
}


@dataclass
class ODTRenderer:
    block_start_string: str
    block_end_string: str
    variable_start_string: str
    variable_end_string: str
    render_func: Callable[[str, dict], str]

    def __post_init__(self):
        self._compile_tags_expressions()
        self._compile_escape_expressions()

    def _compile_tags_expressions(self):
        self.tag_pattern = re.compile(
            rf"(?is)^({self.variable_start_string}|{self.block_start_string}).*({self.variable_end_string}|{self.block_end_string})$"
        )

        self.variable_pattern = re.compile(rf"(?is)({self.variable_start_string})(.*)({self.variable_end_string})$")

        self.block_pattern = re.compile(rf"(?is)({self.block_start_string})(.*)({self.block_end_string})$")

    def _compile_escape_expressions(self):
        # Compiles escape expressions
        self.escape_map = {}
        unescape_rules = {
            r"&gt;": r">",
            r"&lt;": r"<",
            r"&amp;": r"&",
            r"&quot;": r'"',
            r"&apos;": r"'",
        }

        for key, value in unescape_rules.items():
            exp = r"(?is)(({0}|{1})[^{3}{4}]*?)({2})([^{0}{1}]*?({3}|{4}))"
            k = re.compile(
                exp.format(
                    self.variable_start_string,
                    self.block_start_string,
                    key,
                    self.variable_end_string,
                    self.block_end_string,
                )
            )

            self.escape_map[k] = rf"\1{value}\4"

    def _is_template_tag(self, tag: str):
        """
        Returns True is tag (str) is a valid template instruction tag.
        """

        return len(self.tag_pattern.findall(tag)) > 0

    def _is_block_tag(self, tag: str):
        """
        Returns True is tag (str) is a template flow control tag.
        """
        return len(self.block_pattern.findall(tag)) > 0

    def _tags_in_document(self, document: Document):
        """
        Yields a list of available template instructions tags in document.
        """
        tags = document.getElementsByTagName("text:text-input")

        for tag in tags:
            if not tag.hasChildNodes():
                continue

            content = tag.childNodes[0].data.strip()
            if not self._is_template_tag(content):
                continue

            yield tag

    def _census_tags(self, document: Document):
        """
        Make a census of all available template tags in document. We count all
        the children tags nodes within their parents. This process is necesary
        to automaticaly avoid generating invalid documents when mixing block
        tags in differents parts of a document.
        """
        for tag in self._tags_in_document(document):
            content = tag.childNodes[0].data.strip()
            is_block = self._is_block_tag(content)

            count_node_descendant_tags(tag.parentNode, is_block)

    def _prepare_tags(self, document: Document):
        """Here we search for every field node present in xml_document.
        For each field we found we do:
        * if field is a print field ({{ field }}), we replace it with a
          <text:span> node.

        * if field is a control flow ({% %}), then we find immediate node of
          type indicated in field's `text:description` attribute and replace
          the whole node and its childrens with field's content.

          If `text:description` attribute starts with `before::` or `after::`,
          then we move field content before or after the node in description.

          If no `text:description` is available, find the immediate common
          parent of this and any other field and replace its child and
          original parent of field with the field content.

          e.g.: original
          <table>
              <table:row>
                  <field>{% for bar in bars %}</field>
              </table:row>
              <paragraph>
                  <field>{{ bar }}</field>
              </paragraph>
              <table:row>
                  <field>{% endfor %}</field>
              </table:row>
          </table>

          After processing:
          <table>
              {% for bar in bars %}
              <paragraph>
                  <text:span>{{ bar }}</text:span>
              </paragraph>
              {% endfor %}
          </table>
        """

        self._census_tags(document)

        # We have to replace a node, let's call it "placeholder", with the
        # content of our jinja tag. The placeholder can be a node with all its
        # children. Node's "text:description" attribute indicates how far we
        # can scale up in the tree hierarchy to get our placeholder node. When
        # said attribute is not present, then we scale up until we find a
        # common parent for this tag and any other tag.
        for tag in self._tags_in_document(document):
            placeholder = tag
            content = tag.childNodes[0].data.strip()
            is_block = self._is_block_tag(content)
            scale_to = tag.getAttribute("text:description").strip().lower()

            if content.lower().find("|markdown") > 0:
                # Take whole paragraph when handling a markdown field
                scale_to = "text:p"

            if scale_to:
                if FLOW_REFERENCES.get(scale_to, False):
                    placeholder = get_node_parent_of_name(tag, FLOW_REFERENCES[scale_to])

                new_node = document.createTextNode(content)

            elif is_block:
                # expand up the placeholder until a shared parent is found
                while not placeholder.parentNode.tags_count > 1:
                    placeholder = placeholder.parentNode

                if placeholder:
                    new_node = document.createTextNode(content)

            else:
                new_node = document.createElement("text:span")
                text_node = document.createTextNode(content)
                new_node.appendChild(text_node)

            placeholder_parent = placeholder.parentNode
            if not scale_to.startswith("after::"):
                placeholder_parent.insertBefore(new_node, placeholder)
            elif placeholder.isSameNode(placeholder_parent.lastChild):
                placeholder_parent.appendChild(new_node)
            else:
                placeholder_parent.insertBefore(new_node, placeholder.nextSibling)

            if scale_to.startswith(("after::", "before::")):
                # Don't remove whole field tag, only "text:text-input" container
                placeholder = get_node_parent_of_name(tag, "text:p")
                placeholder_parent = placeholder.parentNode

            # Finally, remove the placeholder
            placeholder_parent.removeChild(placeholder)

    def _unescape_entities(self, xml_text: str):
        """
        Unescape links and '&amp;', '&lt;', '&quot;' and '&gt;' within jinja
        instructions. The regexs rules used here are compiled in
        _compile_escape_expressions.
        """
        for regexp, replacement in self.escape_map.items():
            while True:
                xml_text, substitutions = regexp.subn(replacement, xml_text)
                if not substitutions:
                    break

        return self._unescape_links(xml_text)

    def _unescape_links(self, xml_text: str):
        """Fix Libreoffice auto escaping of xlink:href attribute values.
        This unescaping is only done on 'secretary' scheme URLs."""
        robj = re.compile(r"(?is)(xlink:href=\")secretary:(.*?)(\")")

        def replacement(match):
            return Markup(
                "".join(
                    [
                        match.group(1),
                        self.variable_pattern.sub(r"\1 SafeValue(\2) \3", unquote(match.group(2))),
                        match.group(3),
                    ]
                )
            )

        while True:
            xml_text, rep = robj.subn(replacement, xml_text)
            if not rep:
                break

        return xml_text

    def render_xml(self, xml_document: Document, context: dict) -> Document:
        self._prepare_tags(xml_document)
        xml_source = xml_document.toxml()
        rendered_xml = self.render_func(self._unescape_entities(xml_source), context)

        try:
            return parseString(rendered_xml.encode("ascii", "xmlcharrefreplace"))
        except ExpatError as e:
            n_context_chars = 38
            line = rendered_xml.split("\n")[e.lineno - 1]
            lower = max(0, e.offset - n_context_chars)
            upper = min(e.offset + n_context_chars, len(line))
            error_context = line[lower:upper]
            sep = "-" * (e.offset - lower) + "^"
            e.args = (f"Invalid XML near line {e.lineno}, column {e.offset}\n{error_context}\n{sep}",)
            raise

    def render(self, template: ODTTemplate, context: dict) -> None:
        rendered_content = self.render_xml(template.content, context)
        render_images(rendered_content, image_writer=template.add_image)
        template.content.getElementsByTagName("office:document-content")[0].replaceChild(
            rendered_content.getElementsByTagName("office:body")[0],
            template.content.getElementsByTagName("office:body")[0],
        )

        template.styles = self.render_xml(template.styles, context)


def render_images(xml_document: Document, image_writer: Callable[[Path, str], str]):
    """
    This function identifies all image frames in the provided XML document and updates their 'href' attributes.
    The function uses the image's path as the name and employs the ODT file's image writer to save the image and retrieve its path.
    This path is then set as the 'href' attribute for the corresponding image frame in the XML document.
    """
    frames = xml_document.getElementsByTagName("draw:frame")

    for frame in frames:
        if not frame.hasChildNodes():
            continue

        image = Path(frame.getAttribute("draw:name"))

        if not (image.exists() and image.is_file()):
            logger.debug("Image file not found", extra={"image": image})
            continue

        image_node = frame.childNodes[0]
        media_path = image_writer(image, image.stem)
        frame.setAttribute("draw:name", image.stem)
        image_node.setAttribute("xlink:href", media_path)


def get_node_parent_of_name(node: Node, name: str) -> Node | str:
    """
    Returns the node's parent with name equal to *name*.
    Returns None if a parent with that name is not found.
    """
    if not hasattr(node, "parentNode"):
        return None

    if node.parentNode.nodeName.lower() == name.lower():
        return node.parentNode

    # Look into node's grandparent
    return get_node_parent_of_name(node.parentNode, name)


def count_node_descendant_tags(node: Node, is_block_tag: bool):
    """
    Increment *node* tags_count property and block_count property
    if *is_block_tag* is True. Otherwise increase *var_count* property.
    This is also done recursively for this node parents.
    """
    if not node:
        return

    # start counter
    for attr in ["tags_count", "block_count", "var_count"]:
        if not hasattr(node, attr):
            setattr(node, attr, 0)

    node.tags_count += 1
    count_var_name = "block_count" if is_block_tag else "var_count"
    setattr(node, count_var_name, getattr(node, count_var_name) + 1)
    count_node_descendant_tags(node.parentNode, is_block_tag)
