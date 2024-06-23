import io
import logging
import re
import zipfile
from mimetypes import guess_extension, guess_type
from pathlib import Path
from xml.dom.minidom import parseString

from markdown2 import markdown
from markupsafe import Markup

from python_odt_template.markdown_map import transform_map

basestring = (str, bytes)

logger = logging.getLogger("python_odt_template")


class ODTFile:
    """An abstraction over an ODT file."""

    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)
        self.files = self.unpack_template(file_path)
        self.content = parseString(self.files["content.xml"])
        self.styles = parseString(self.files["styles.xml"])
        self.manifest = parseString(self.files["META-INF/manifest.xml"])

    def add_image(self, filepath: Path, name: str) -> str:
        file_type = guess_type(filepath)
        mime = file_type[0] if file_type[0] else "image/png"  # FIXME
        extension = filepath.suffix if filepath.suffix else guess_extension(mime)

        media_path = f"Pictures/{name}{extension}"
        self.files[media_path] = filepath.read_bytes()

        files_node = self.manifest.getElementsByTagName("manifest:manifest")[0]
        node = self.manifest.createElement("manifest:file-entry")
        if files_node:
            files_node.appendChild(node)
        node.setAttribute("manifest:full-path", media_path)
        node.setAttribute("manifest:media-type", mime)
        return media_path

    @classmethod
    def unpack_template(cls, template: Path) -> dict:
        # And Open/libreOffice is just a ZIP file. Here we unarchive the file
        # and return a dict with every file in the archive
        logger.debug("Unpacking template file")

        archive_files = {}
        archive = zipfile.ZipFile(template, "r")
        for zfile in archive.filelist:
            archive_files[zfile.filename] = archive.read(zfile.filename)

        return archive_files

    @classmethod
    def pack_document(cls, files: dict) -> io.BytesIO:
        # Store to a zip files in files
        logger.debug("packing document")
        zip_file = io.BytesIO()

        mimetype = files["mimetype"]
        del files["mimetype"]

        zipdoc = zipfile.ZipFile(zip_file, "a", zipfile.ZIP_DEFLATED)

        # Store mimetype without without compression using a ZipInfo object
        # for compatibility with Py2.6 which doesn't have compress_type
        # parameter in ZipFile.writestr function
        mime_zipinfo = zipfile.ZipInfo("mimetype")
        zipdoc.writestr(mime_zipinfo, mimetype)

        for fname, content in files.items():
            zipdoc.writestr(fname, content)

        logger.debug("Document packing completed")

        return zip_file

    def get_markdown_filter(self):
        def markdown_filter(markdown_text):
            """
            Convert a markdown text into a ODT formated text
            """

            def get_style_by_name(style_name):
                """
                Search in <office:automatic-styles> for style_name.
                Return None if style_name is not found. Otherwise
                return the style node
                """

                auto_styles = self.content.getElementsByTagName("office:automatic-styles")[0]

                if not auto_styles.hasChildNodes():
                    return None

                for style_node in auto_styles.childNodes:
                    if style_node.hasAttribute("style:name") and (
                            style_node.getAttribute("style:name") == style_name
                    ):
                        return style_node

                return None

            def insert_style_in_content(style_name, attributes=None, **style_properties):
                """
                Insert a new style into content.xml's <office:automatic-styles> node.
                Returns a reference to the newly created node
                """

                auto_styles = self.content.getElementsByTagName("office:automatic-styles")[0]
                style_node = self.content.createElement("style:style")

                style_node.setAttribute("style:name", style_name)
                style_node.setAttribute("style:family", "text")
                style_node.setAttribute("style:parent-style-name", "Standard")

                if attributes:
                    for k, v in attributes.items():
                        style_node.setAttribute("style:%s" % k, v)

                if style_properties:
                    style_prop = self.content.createElement("style:text-properties")
                    for k, v in style_properties.items():
                        style_prop.setAttribute("%s" % k, v)

                    style_node.appendChild(style_prop)

                return auto_styles.appendChild(style_node)

            if not isinstance(markdown_text, basestring):
                return ""

            styles_cache = {}  # cache styles searching
            html_text = markdown(markdown_text)
            encoded = html_text.encode("ascii", "xmlcharrefreplace")
            if isinstance(encoded, bytes):
                # In PY3 bytes-like object needs convert to str
                encoded = encoded.decode("ascii")
            xml_object = parseString("<html>%s</html>" % encoded)

            # Transform HTML tags as specified in transform_map
            # Some tags may require extra attributes in ODT.
            # Additional attributes are indicated in the 'attributes' property

            for tag in transform_map:
                html_nodes = xml_object.getElementsByTagName(tag)
                for html_node in html_nodes:
                    odt_node = xml_object.createElement(transform_map[tag]["replace_with"])

                    # Transfer child nodes
                    if html_node.hasChildNodes():
                        # We can't directly insert text into a text:list-item element.
                        # The content of the item most be wrapped inside a container
                        # like text:p. When there's not a double linebreak separating
                        # list elements, markdown2 creates <li> elements without wraping
                        # their contents inside a container. Here we automatically create
                        # the container if one was not created by markdown2.
                        if tag == "li" and html_node.childNodes[0].localName != "p":
                            container = xml_object.createElement("text:p")
                            odt_node.appendChild(container)
                        elif tag == "code":

                            def traverse_preformated(node):
                                if node.hasChildNodes():
                                    for n in node.childNodes:
                                        traverse_preformated(n)
                                else:
                                    container = xml_object.createElement("text:span")
                                    for text in re.split(
                                            "(\n)", node.nodeValue.lstrip("\n")
                                    ):
                                        if text == "\n":
                                            container.appendChild(
                                                xml_object.createElement("text:line-break")
                                            )
                                        else:
                                            container.appendChild(
                                                xml_object.createTextNode(text)
                                            )

                                    node.parentNode.replaceChild(container, node)

                            traverse_preformated(html_node)
                            container = odt_node
                        else:
                            container = odt_node

                        for child_node in html_node.childNodes:
                            container.appendChild(child_node.cloneNode(True))

                    # Add style-attributes defined in transform_map
                    if "style_attributes" in transform_map[tag]:
                        for k, v in transform_map[tag]["style_attributes"].items():
                            odt_node.setAttribute("text:%s" % k, v)

                    # Add defined attributes
                    if "attributes" in transform_map[tag]:
                        for k, v in transform_map[tag]["attributes"].items():
                            odt_node.setAttribute(k, v)

                        # copy original href attribute in <a> tag
                        if tag == "a":
                            if html_node.hasAttribute("href"):
                                odt_node.setAttribute(
                                    "xlink:href", html_node.getAttribute("href")
                                )

                    # Does the node need to create an style?
                    if "style" in transform_map[tag]:
                        name = transform_map[tag]["style"]["name"]
                        if name not in styles_cache:
                            style_node = get_style_by_name(name)

                            if style_node is None:
                                # Create and cache the style node
                                style_node = insert_style_in_content(
                                    name,
                                    transform_map[tag]["style"].get("attributes", None),
                                    **transform_map[tag]["style"]["properties"]
                                )
                                styles_cache[name] = style_node

                    html_node.parentNode.replaceChild(odt_node, html_node)

            ODTText = "".join(
                node_as_str
                for node_as_str in map(
                    lambda node: node.toxml(),
                    xml_object.getElementsByTagName("html")[0].childNodes,
                )
            )

            return Markup(ODTText)

        return markdown_filter
