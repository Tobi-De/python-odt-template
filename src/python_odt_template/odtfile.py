import logging
import zipfile
from pathlib import Path
import io
from os import path
from mimetypes import  guess_extension
from xml.dom.minidom import parseString

logger = logging.getLogger("python_odt_template")


class ODTFile:
    """An abstraction over an ODT file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.files = self.unpack_template(file_path)
        self.content = parseString(self.files["content.xml"])
        self.styles = parseString(self.files["styles.xml"])
        self.manifest = parseString(self.files["META-INF/manifest.xml"])

    def add_media_to_archive(self, media, mime, name=""):
        """
        Adds to "Pictures" archive folder the file in `media` and register
        it into manifest file.
        """
        extension = None
        if hasattr(media, "name") and not name:
            extension = path.splitext(media.name)
            name = extension[0]
            extension = extension[1]

        if not extension:
            extension = guess_extension(mime)

        media_path = "Pictures/%s%s" % (name, extension)
        media.seek(0)
        self.files[media_path] = media.read(-1)
        if hasattr(media, "close"):
            media.close()

        files_node = self.manifest.getElementsByTagName("manifest:manifest")[0]
        node = self.create_node(self.manifest, "manifest:file-entry", files_node)
        node.setAttribute("manifest:full-path", media_path)
        node.setAttribute("manifest:media-type", mime)

        return media_path

    @classmethod
    def create_node(cls, xml_document, node_type, parent=None):
        """Creates a node in `xml_document` of type `node_type` and specified,
        as child of `parent`."""
        node = xml_document.createElement(node_type)
        if parent:
            parent.appendChild(node)

        return node

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