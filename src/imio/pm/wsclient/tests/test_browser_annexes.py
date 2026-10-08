# -*- coding: utf-8 -*-
"""browser/annexes.py: file reader of the Archetypes files sent as annexes (F12)."""
from imio.pm.wsclient.browser.annexes import ATRawReadFile
from imio.pm.wsclient.testing import WS4PMClientTestCase
from zope.filerepresentation.interfaces import IRawReadFile

import unittest


try:
    from Products.ATContentTypes.interfaces import IATFile
except ImportError:  # Plone 5.2+: no Archetypes
    IATFile = None


@unittest.skipIf(IATFile is None, "Archetypes File only")
class TestATRawReadFile(WS4PMClientTestCase):
    def setUp(self):
        super(TestATRawReadFile, self).setUp()
        self.reader = IRawReadFile(
            self.create_file(self.portal, data=b"hello\nworld\n")
        )

    def test___init__(self):
        self.assertIsInstance(self.reader, ATRawReadFile)

    def test_size(self):
        self.assertEqual(self.reader.size(), 12)

    def test_read(self):
        self.assertEqual(self.reader.read(), b"hello\nworld\n")
        self.assertEqual(self.reader.read(2), b"he")

    @unittest.expectedFailure
    def test_readline(self):
        """Master bug: AttributeError, the blob iterator of the file has no readline."""
        self.assertEqual(self.reader.readline(), b"hello\n")
        self.assertEqual(self.reader.readline(2), b"he")

    @unittest.expectedFailure
    def test_readlines(self):
        """Master bug: AttributeError, the blob iterator of the file has no readlines."""
        self.assertEqual(self.reader.readlines(), [b"hello\n", b"world\n"])
        self.assertEqual(self.reader.readlines(1), [b"hello\n"])

    def test_next(self):
        self.assertEqual(next(iter(self.reader)), b"hello\nworld\n")

    def test_name(self):
        self.assertEqual(self.reader.name, u"annexe oubliée.txt".encode("utf-8"))

    @unittest.expectedFailure
    def test_encoding(self):
        """Master bug: AttributeError, ATRawReadFile has no _getMessage."""
        self.assertEqual(self.reader.encoding, "utf-8")
