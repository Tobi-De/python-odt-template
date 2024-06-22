import logging
from mimetypes import guess_type
from urllib.parse import unquote
from jinja2 import Environment, Undefined
from xml.dom.minidom import parseString, Document
from xml.parsers.expat import ExpatError, ErrorString
from markupsafe import Markup
from os import path
import re
from python_odt_template.jinja_filters import (
    pad_string,
    get_markdown_filter,
    get_image_filter,
    finalize_value,
)

xrange = range
basestring = (str, bytes)

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


class ODTTemplateEngine:
    def __init__(
        self,
        content: Document,
        add_media_file: callable,
        environment: Environment = None,
        media_path: str = ".",
    ):

        if environment:
            self.environment = environment
        else:
            self.environment = Environment(
                undefined=UndefinedSilently,
                autoescape=True,
                finalize=finalize_value,
            )

        self.media_path = media_path
        self.media_callback = self.fs_loader
        self.template_images = {}
        self.add_media_to_archive = add_media_file

        self.environment.filters["pad"] = pad_string
        self.environment.globals["SafeValue"] = Markup

        self.environment.filters["markdown"] = get_markdown_filter(content)
        self.environment.filters["image"] = get_image_filter(self)

        self._compile_tags_expressions()

    # def media_loader(self, callback):
    #     """This sets the the media loader. A user defined function which
    #     loads media. The function should take a template value, optionals
    #     args and kwargs. Is media exists should return a tuple whose first
    #     element if a file object type representing the media and its second
    #     elements is the media mimetype.
    #
    #     See Renderer.fs_loader funcion for an example"""
    #     self.media_callback = callback
    #     return callback

    @classmethod
    def _inc_node_tags_count(cls, node, is_block=False):
        """Increase field count of node and its parents"""

        if node is None:
            return

        for attr in ["field_count", "block_count", "var_count"]:
            if not hasattr(node, attr):
                setattr(node, attr, 0)

        node.field_count += 1
        if is_block:
            node.block_count += 1
        else:
            node.var_count += 1

        cls._inc_node_tags_count(node.parentNode, is_block)

    def _compile_tags_expressions(self):
        self.tag_pattern = re.compile(
            r"(?is)^({0}|{1}).*({2}|{3})$".format(
                self.environment.variable_start_string,
                self.environment.block_start_string,
                self.environment.variable_end_string,
                self.environment.block_end_string,
            )
        )

        self.variable_pattern = re.compile(
            r"(?is)({0})(.*)({1})$".format(
                self.environment.variable_start_string,
                self.environment.variable_end_string,
            )
        )

        self.block_pattern = re.compile(
            r"(?is)({0})(.*)({1})$".format(
                self.environment.block_start_string, self.environment.block_end_string
            )
        )

        self._compile_escape_expressions()

    def _compile_escape_expressions(self):
        # Compiles escape expressions
        self.escape_map = dict()
        unescape_rules = {
            r"&gt;": r">",
            r"&lt;": r"<",
            r"&amp;": r"&",
            r"&quot;": r'"',
            r"&apos;": r"\'",
        }

        for key, value in unescape_rules.items():
            exp = r"(?is)(({0}|{1})[^{3}{4}]*?)({2})([^{0}{1}]*?({3}|{4}))"
            key = re.compile(
                exp.format(
                    self.environment.variable_start_string,
                    self.environment.block_start_string,
                    key,
                    self.environment.variable_end_string,
                    self.environment.block_end_string,
                )
            )

            self.escape_map[key] = r"\1{0}\4".format(value)

    def _is_jinja_tag(self, tag):
        """
        Returns True is tag (str) is a valid jinja instruction tag.
        """

        return len(self.tag_pattern.findall(tag)) > 0

    def _is_block_tag(self, tag):
        """
        Returns True is tag (str) is a jinja flow control tag.
        """
        return len(self.block_pattern.findall(tag)) > 0

    def _tags_in_document(self, document):
        """
        Yields a list of available jinja instructions tags in document.
        """
        tags = document.getElementsByTagName("text:text-input")

        for tag in tags:
            if not tag.hasChildNodes():
                continue

            content = tag.childNodes[0].data.strip()
            if not self._is_jinja_tag(content):
                continue

            yield tag

    def _census_tags(self, document):
        """
        Make a census of all available jinja tags in document. We count all
        the children tags nodes within their parents. This process is necesary
        to automaticaly avoid generating invalid documents when mixing block
        tags in differents parts of a document.
        """
        for tag in self._tags_in_document(document):
            content = tag.childNodes[0].data.strip()
            block_tag = self._is_block_tag(content)

            self._inc_node_tags_count(tag.parentNode, block_tag)

    def _prepare_document_tags(self, document: Document):
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

        # -------------------------------------------------------------------- #
        # We have to replace a node, let's call it "placeholder", with the
        # content of our jinja tag. The placeholder can be a node with all its
        # children. Node's "text:description" attribute indicates how far we
        # can scale up in the tree hierarchy to get our placeholder node. When
        # said attribute is not present, then we scale up until we find a
        # common parent for this tag and any other tag.
        # -------------------------------------------------------------------- #
        logger.debug("Preparing document tags")
        self._census_tags(document)

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
                    placeholder = self._parent_of_type(tag, FLOW_REFERENCES[scale_to])

                new_node = document.createTextNode(content)

            elif is_block:
                # expand up the placeholder until a shared parent is found
                while not placeholder.parentNode.field_count > 1:
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
            else:
                if placeholder.isSameNode(placeholder_parent.lastChild):
                    placeholder_parent.appendChild(new_node)
                else:
                    placeholder_parent.insertBefore(new_node, placeholder.nextSibling)

            if scale_to.startswith(("after::", "before::")):
                # Don't remove whole field tag, only "text:text-input" container
                placeholder = self._parent_of_type(tag, "text:p")
                placeholder_parent = placeholder.parentNode

            # Finally, remove the placeholder
            placeholder_parent.removeChild(placeholder)

    def _unescape_entities(self, xml_text):
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

    def _unescape_links(self, xml_text):
        """Fix Libreoffice auto escaping of xlink:href attribute values.
        This unescaping is only done on 'secretary' scheme URLs."""
        robj = re.compile(r"(?is)(xlink:href=\")secretary:(.*?)(\")")

        def replacement(match):
            return Markup(
                "".join(
                    [
                        match.group(1),
                        self.variable_pattern.sub(
                            r"\1 SafeValue(\2) \3", unquote(match.group(2))
                        ),
                        match.group(3),
                    ]
                )
            )

        while True:
            xml_text, rep = robj.subn(replacement, xml_text)
            if not rep:
                break

        return xml_text

    def fs_loader(self, media, *args, **kwargs):
        """Loads a file from the file system.
        :param media: A file object or a relative or absolute path of a file.
        :type media: unicode
        """
        if hasattr(media, "seek") and hasattr(media, "read"):
            return (media, "image/jpeg")
        elif path.isfile(media):
            filename = media
        else:
            if not self.media_path:
                logger.debug("media_path property not specified to load images from.")
                return

            filename = path.join(self.media_path, media)
            if not path.isfile(filename):
                logger.debug('Media file "%s" does not exists.' % filename)
                return

        mime = guess_type(filename)
        return (open(filename, "rb"), mime[0] if mime else None)

    def replace_images(self, xml_document: Document):
        """Perform images replacements"""
        logger.debug("Inserting images")
        frames = xml_document.getElementsByTagName("draw:frame")

        for frame in frames:
            if not frame.hasChildNodes():
                continue

            key = frame.getAttribute("draw:name")
            if key not in self.template_images:
                continue

            # Get frame attributes
            frame_attrs = dict()
            for i in xrange(frame.attributes.length):
                attr = frame.attributes.item(i)
                frame_attrs[attr.name] = attr.value

            # Get child draw:image node and its attrs
            image_node = frame.childNodes[0]
            image_attrs = dict()
            for i in xrange(image_node.attributes.length):
                attr = image_node.attributes.item(i)
                image_attrs[attr.name] = attr.value

            # Request to media loader the image to use
            image = self.media_callback(
                self.template_images[key]["value"],
                *self.template_images[key]["args"],
                frame_attrs=frame_attrs,
                image_attrs=image_attrs,
                **self.template_images[key]["kwargs"]
            )

            # Update frame and image node attrs (if they where updated in
            # media_callback call)
            for k, v in frame_attrs.items():
                frame.setAttribute(k, v)

            for k, v in image_attrs.items():
                image_node.setAttribute(k, v)

            # Keep original image reference value
            if isinstance(self.template_images[key]["value"], basestring):
                frame.setAttribute("draw:name", self.template_images[key]["value"])

            # Does the madia loader returned something?
            if not image:
                continue

            mname = self.add_media_to_archive(media=image[0], mime=image[1], name=key)
            if mname:
                image_node.setAttribute("xlink:href", mname)

    def render_xml(self, xml_document: Document, **kwargs):
        # Prepare the xml object to be processed by jinja2
        logger.debug("Rendering XML object")
        template_string = ""

        try:
            self.template_images = dict()
            self._prepare_document_tags(xml_document)
            xml_source = xml_document.toxml()
            xml_source = xml_source.encode("ascii", "xmlcharrefreplace")
            jinja_template = self.environment.from_string(
                self._unescape_entities(xml_source.decode("utf-8"))
            )

            result = jinja_template.render(**kwargs)

            final_xml = parseString(result.encode("ascii", "xmlcharrefreplace"))
            if self.template_images:
                self.replace_images(final_xml)

            return final_xml
        except ExpatError as e:
            if not "result" in locals():
                result = xml_source
            near = result.split("\n")[e.lineno - 1][e.offset - 200 : e.offset + 200]

            raise ExpatError(
                'ExpatError "%s" at line %d, column %d\nNear of: "[...]%s[...]"'
                % (ErrorString(e.code), e.lineno, e.offset, near)
            )
        except:
            logger.error(
                "Error rendering template:\n%s",
                xml_document.toprettyxml(),
                exc_info=True,
            )

            logger.error("Unescaped template was:\n{0}".format(template_string))
            raise
        finally:
            logger.debug("Rendering xml object finished")

    def _parent_of_type(self, node, of_type):
        # Returns the first immediate parent of type `of_type`.
        # Returns None if nothing is found.

        if hasattr(node, "parentNode"):
            if node.parentNode.nodeName.lower() == of_type:
                return node.parentNode
            else:
                return self._parent_of_type(node.parentNode, of_type)
        else:
            return None


class UndefinedSilently(Undefined):
    # Silently undefined,
    # see http://stackoverflow.com/questions/6182498
    def silently_undefined(*args, **kwargs):
        return ""

    return_new = lambda *args, **kwargs: UndefinedSilently()

    __unicode__ = silently_undefined
    __str__ = silently_undefined
    __call__ = return_new
    __getattr__ = return_new

