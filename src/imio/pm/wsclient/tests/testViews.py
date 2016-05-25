# -*- coding: utf-8 -*-
#
# File: testItemMethods.py
#
# Copyright (c) 2012 by CommunesPlone
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.ws.config import POD_TEMPLATE_ID_PATTERN

from imio.pm.wsclient.config import CORRECTLY_SENT_TO_PM_INFO
from imio.pm.wsclient.config import FILENAME_MANDATORY_ERROR
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import UNABLE_TO_DETECT_MIMETYPE_ERROR
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import cleanMemoize
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import createDocument
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase


class testViews(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """
    def test_generateItemTemplateView(self):
        """
          Test the BrowserView that generates a given template of an item
        """
        self.changeUser('admin')
        messages = IStatusMessage(self.request)
        document = createDocument(self.portal)
        DOCUMENT_ABSOLUTE_URL = document.absolute_url()
        # we must obviously be connected to PM...
        view = document.restrictedTraverse('@@generate_document_from_plonemeeting')
        # nothing is generated, just redirected to the context
        self.assertFalse(view() != DOCUMENT_ABSOLUTE_URL)
        self.assertTrue(len(messages.show()) == 1)
        self.assertTrue(messages.show()[0].message == UNABLE_TO_CONNECT_ERROR)
        #_soap_connectToPloneMeeting is memoized...
        cleanMemoize(self.request)
        item = self._sendToPloneMeeting(document)
        # a statusmessage for having created the item successfully
        self.assertEqual(messages.show()[-1].message, CORRECTLY_SENT_TO_PM_INFO)
        view = document.restrictedTraverse('@@generate_document_from_plonemeeting')
        # with no templateFormat defined, the mimetype can not be determined
        # an error statusmessage is displayed
        # last added statusmessage
        # nothing is generated, just redirected to the context
        self.assertFalse(view() != DOCUMENT_ABSOLUTE_URL)
        self.assertEqual(messages.show()[-1].message, UNABLE_TO_DETECT_MIMETYPE_ERROR)
        self.request.set('templateFormat', 'odt')
        # if no templateFilename, an error is displayed, nothing is generated
        view = document.restrictedTraverse('@@generate_document_from_plonemeeting')
        # nothing is generated, just redirected to the context
        self.assertFalse(view() != DOCUMENT_ABSOLUTE_URL)
        self.assertEqual(messages.show()[-1].message, FILENAME_MANDATORY_ERROR)
        # if not valid itemUID defined, the item can not be found and so accessed
        self.request.set('templateFilename', 'filename')
        view = document.restrictedTraverse('@@generate_document_from_plonemeeting')
        # nothing is generated, just redirected to the context
        self.assertFalse(view() != DOCUMENT_ABSOLUTE_URL)
        self.assertEqual(
            messages.show()[-1].message, u"An error occured while generating the document in "
            "PloneMeeting!  The error message was : Server raised fault: 'You can not access this item!'"
        )
        # now with a valid itemUID but no valid templateId
        self.request.set('itemUID', item.UID())
        view = document.restrictedTraverse('@@generate_document_from_plonemeeting')
        # nothing is generated, just redirected to the context
        self.assertFalse(view() != DOCUMENT_ABSOLUTE_URL)
        self.assertEqual(
            messages.show()[-1].message, u"An error occured while generating the document in "
            "PloneMeeting!  The error message was : Server raised fault: 'You can not access this template!'"
        )
        # now with all valid infos
        self.request.set('templateId', POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt'))
        view = document.restrictedTraverse('@@generate_document_from_plonemeeting')
        res = view()
        # with have a real result, aka not redirected to the context, a file
        self.assertTrue(view() != DOCUMENT_ABSOLUTE_URL)
        self.assertTrue(len(res) > 10000)
        self.assertEquals(self.request.response.headers,
                          {'content-type': 'application/vnd.oasis.opendocument.text',
                           'location': '{0}/document'.format(self.portal.absolute_url()),
                           'content-disposition': 'inline;filename="filename.odt"'})


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testViews, prefix='test_'))
    return suite
