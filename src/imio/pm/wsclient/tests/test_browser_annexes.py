# -*- coding: utf-8 -*-
"""browser/annexes.py: file reader of the Files sent as annexes (F12)."""
from imio.pm.wsclient.browser.annexes import FileRawReadFile
from imio.pm.wsclient.testing import WS4PMClientTestCase
from zope.filerepresentation.interfaces import IRawReadFile


class TestFileRawReadFile(WS4PMClientTestCase):
    def setUp(self):
        super(TestFileRawReadFile, self).setUp()
        self.reader = IRawReadFile(
            self.create_file(self.portal, data=b"hello\nworld\n")
        )

    def test___init__(self):
        self.assertIsInstance(self.reader, FileRawReadFile)

    def test_size(self):
        self.assertEqual(self.reader.size(), 12)

    def test_read(self):
        self.assertEqual(self.reader.read(2), b"he")
        self.assertEqual(self.reader.read(), b"llo\nworld\n")

    def test_readline(self):
        self.assertEqual(self.reader.readline(), b"hello\n")

    def test_readlines(self):
        self.assertEqual(self.reader.readlines(), [b"hello\n", b"world\n"])

    def test___next__(self):
        self.assertEqual(next(iter(self.reader)), b"hello\n")

    def test_name(self):
        self.assertEqual(self.reader.name, u"annexe oubliée.txt")

    def test_mimeType(self):
        self.assertEqual(self.reader.mimeType, "text/plain")
