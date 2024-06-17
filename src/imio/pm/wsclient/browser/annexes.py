# -*- coding: utf-8 -*-

from zope.filerepresentation.interfaces import IRawReadFile
from zope.interface import implementer


@implementer(IRawReadFile)
class ATRawReadFile(object):
    """
    """
    encoding = 'utf-8'
    name = None

    def __init__(self, context):
        self.context = context
        self._size = 0

    def size(self):
        stream = self._getStream()
        pos = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(pos)
        return size

    def read(self, size=None):
        if size is not None:
            return self._getStream().read(size)
        else:
            return self._getStream().read()

    def readline(self, size=None):
        if size is None:
            return self._getStream().readline()
        else:
            return self._getStream().readline(size)

    def readlines(self, sizehint=None):
        if sizehint is None:
            return self._getStream().readlines()
        else:
            return self._getStream().readlines(sizehint)

    def _getStream(self):
        return self.context.getFile().getIterator()

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._getStream())

    @property
    def encoding(self):
        return self._getMessage().get_charset() or 'utf-8'

    @property
    def name(self):
        return self.context.getFilename()
