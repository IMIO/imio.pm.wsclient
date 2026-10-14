# -*- coding: utf-8 -*-

from io import BytesIO
from plone.dexterity.filerepresentation import ReadFileBase
from zope.filerepresentation.interfaces import IRawReadFile
from zope.interface import implementer


@implementer(IRawReadFile)
class FileRawReadFile(ReadFileBase):
    """Raw data of a File sent as annex (plone.dexterity's default reader
    returns an RFC822 message)."""

    @property
    def name(self):
        return self.context.file.filename

    @property
    def mimeType(self):
        return self.context.file.contentType

    def _getStream(self):
        if not hasattr(self, "_stream"):
            self._stream = BytesIO(self.context.file.data)
        return self._stream

    def __next__(self):
        return next(self._getStream())
