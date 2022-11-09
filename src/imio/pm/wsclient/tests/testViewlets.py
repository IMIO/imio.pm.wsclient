# -*- coding: utf-8 -*-
#
# File: testViewlets.py
#
# GNU General Public License (GPL)
#

from Products.statusmessages.interfaces import IStatusMessage
from imio.pm.wsclient.browser.viewlets import PloneMeetingInfosViewlet
from imio.pm.wsclient.config import CAN_NOT_SEE_LINKED_ITEMS_INFO
from imio.pm.wsclient.config import CORRECTLY_SENT_TO_PM_INFO
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import cleanMemoize
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import createDocument
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from mock import patch
from zope.annotation import IAnnotations

import transaction


class testViewlets(WS4PMCLIENTTestCase):
    """
        Tests the browser.testViewlets methods
    """

    def test_available(self):
        """ """
        self.changeUser('admin')
        document = createDocument(self.portal)
        # by default, no viewlet_display_condition TAL expression
        viewlet = PloneMeetingInfosViewlet(document, self.request, None, None)
        viewlet.update()
        settings = viewlet.ws4pmSettings.settings()
        settings.viewlet_display_condition = u''
        # no items created/linked, so the viewlet is not displayed
        self.assertFalse(viewlet.available())
        # viewlet is displayed depending on :
        # by default, the fact that it is linked to an item
        # or if a TAL expression is defined in the config and returns True
        # test with a defined TAL expression in the configuration
        settings.viewlet_display_condition = u'python: True'
        # if a TAL expression is defined, it take precedence
        # available is memoized so it is still False...
        self.assertFalse(viewlet.available())
        # remove memoized informations
        cleanMemoize(self.request, viewlet)
        self.assertTrue(viewlet.available())
        cleanMemoize(self.request, viewlet)
        # now remove the TAL expression and send the object to PloneMeeting
        settings.viewlet_display_condition = u''
        self.assertFalse(viewlet.available())
        cleanMemoize(self.request, viewlet)
        item = self._sendToPloneMeeting(document)
        # now that the element has been sent, the viewlet is available
        self.assertTrue(viewlet.available())
        cleanMemoize(self.request, viewlet)
        # define a TAL expression taking care of the 'isLinked'
        settings.viewlet_display_condition = u'python: isLinked and object.portal_type == "wrong_value"'
        self.assertFalse(viewlet.available())
        cleanMemoize(self.request, viewlet)
        settings.viewlet_display_condition = u'python: isLinked and object.portal_type == "Document"'
        self.assertTrue(viewlet.available())
        cleanMemoize(self.request, viewlet)
        # if the TAL expression has errors, available is False and a message is displayed
        messages = IStatusMessage(self.request)
        # by default, 2 messages already exist, these are item creation related messages
        shownMessages = messages.show()
        self.assertTrue(len(shownMessages) == 1)
        self.assertTrue(shownMessages[0].message, CORRECTLY_SENT_TO_PM_INFO)
        settings.viewlet_display_condition = u'python: object.getUnexistingAttribute()'
        # in case there is a problem, a message is displayed in a tuple (msg, error_level)
        self.assertTrue(isinstance(viewlet.available(), tuple))
        cleanMemoize(self.request, viewlet)
        # now check when the linked item is removed
        settings.viewlet_display_condition = u''
        self.assertTrue(viewlet.available())
        cleanMemoize(self.request, viewlet)
        item.aq_inner.aq_parent.manage_delObjects(ids=[item.getId(), ])
        transaction.commit()
        self.assertFalse(viewlet.available())

    def test_getPloneMeetingLinkedInfos(self):
        """
          Test the getPloneMeetingLinkedInfos method :
          - if nothing found, an empty {} is returned
          - if elements are found, relevant data are returned
        """
        self.changeUser('admin')
        document = createDocument(self.portal)
        viewlet = PloneMeetingInfosViewlet(document, self.request, None, None)
        viewlet.update()
        self.assertTrue(viewlet.available() is False)
        # now send an element to PloneMeeting and check again
        cleanMemoize(self.request, viewlet)
        item = self._sendToPloneMeeting(document)
        # we received informations about the created item
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos()[0]['UID'] == item.UID())

    @patch("imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_searchItems")
    @patch("imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_getItemInfos")
    def test_getPloneMeetingLinkedInfos_with_linked_items(
        self, _rest_getItemInfos, _rest_searchItems
    ):
        """
        Test getPloneMeetingLinkedInfos method when there is linked items
        """
        _rest_searchItems.return_value = [{
            "@id": "http://nohost/pu-1234",
            "@type": "MeetingItemCollege",
            "UID": "1234",
            "created": "2022-01-01T00:00:00+00:00",
            "modified": "2022-01-01T00:00:00+00:00",
            "id": "pu-1234",
            "title": "PU/1244",
            "review_state": "accepted",
            "description": "Description",
            "extra_include_linked_items": [
                {
                    "@id": "http://nohost/pu-1234-1",
                    "@type": "MeetingItemCollege",
                    "UID": "2345",
                    "created": "2022-01-02T00:00:00+00:00",
                    "modified": "2022-01-02T00:00:00+00:00",
                    "id": "pu-1234-1",
                    "title": "PU/1244-1",
                    "review_state": "accepted",
                    "description": "Description",
                },
                {
                    "@id": "http://nohost/pu-1234-2",
                    "@type": "MeetingItemCollege",
                    "UID": "3456",
                    "created": "2022-01-03T00:00:00+00:00",
                    "modified": "2022-01-03T00:00:00+00:00",
                    "id": "pu-1234-2",
                    "title": "PU/1244-2",
                    "review_state": "accepted",
                    "description": "Description",
                },
            ],
            "extra_include_linked_items_items_total": "2",
        }]
        _rest_getItemInfos.side_effect = [
            [{
                "@id": "http://nohost/pu-1234",
                "@type": "MeetingItemCollege",
                "UID": "1234",
                "created": "2022-01-01T00:00:00+00:00",
                "modified": "2022-01-01T00:00:00+00:00",
                "id": "pu-1234",
                "title": "PU/1244",
                "review_state": "accepted",
                "description": "Description",
                "extra_include_config": {
                    "id": "plonemeeting-assembly",
                }
            }],
            [{
                "@id": "http://nohost/pu-1234-1",
                "@type": "MeetingItemCollege",
                "UID": "2345",
                "created": "2022-01-02T00:00:00+00:00",
                "modified": "2022-01-02T00:00:00+00:00",
                "id": "pu-1234-1",
                "title": "PU/1244-1",
                "review_state": "accepted",
                "description": "Description",
                "extra_include_config": {
                    "id": "plonemeeting-assembly",
                }
            }],
            [{
                "@id": "http://nohost/pu-1234-2",
                "@type": "MeetingItemCollege",
                "UID": "3456",
                "created": "2022-01-03T00:00:00+00:00",
                "modified": "2022-01-03T00:00:00+00:00",
                "id": "pu-1234-2",
                "title": "PU/1244-2",
                "review_state": "accepted",
                "description": "Description",
                "extra_include_config": {
                    "id": "plonegov-assembly",
                }
            }],
        ]
        self.changeUser('admin')
        document = createDocument(self.portal)
        self._sendToPloneMeeting(document)
        viewlet = PloneMeetingInfosViewlet(document, self.request, None, None)
        viewlet.update()
        items = viewlet.getPloneMeetingLinkedInfos()
        self.assertEqual(3, len(items))
        self.assertEqual(
            ["pu-1234-2", "pu-1234-1", "pu-1234"],
            [e["id"] for e in items],
        )

    def test_canNotSeeLinkedInfos(self):
        """
          If the element has been sent to PloneMeeting but current user can not see these
          items in PloneMeeting, a message is displayed
        """
        self.changeUser('admin')
        document = createDocument(self.portal)
        viewlet = PloneMeetingInfosViewlet(document, self.request, None, None)
        viewlet.update()
        item = self._sendToPloneMeeting(document)
        # we received informations about the created item
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos()[0]['UID'] == item.UID())
        # admin will create the element inTheNameOf 'pmCreator1'
        self.changeUser('pmCreator1')
        cleanMemoize(self.request, viewlet)
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos()[0]['UID'] == item.UID())
        # 'pmCreator2' will not see the infos about items, just a message
        self.changeUser('pmCreator2')
        cleanMemoize(self.request, viewlet)
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos() == (CAN_NOT_SEE_LINKED_ITEMS_INFO, 'info'))

    def test_canNotConnectTemporarily(self):
        """
          Test a connection problem in PloneMeeting after an item has already been sent
          - connect to PM successfully
          - send the item successfully
          - break settings
          - check what is going on while not being able to show PM related informations
        """
        self.changeUser('admin')
        document = createDocument(self.portal)
        viewlet = PloneMeetingInfosViewlet(document, self.request, None, None)
        viewlet.update()
        # send an element to PloneMeeting
        item = self._sendToPloneMeeting(document)
        # correctly sent
        self.assertTrue(viewlet.available() is True)
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos()[0]['UID'] == item.UID())
        setCorrectSettingsConfig(self.portal, **{'pm_url': u'http://wrong/url'})
        cleanMemoize(self.request, viewlet)
        # no available
        # a message is returned in the viewlet by the viewlet.available method
        self.assertTrue(viewlet.available() == (UNABLE_TO_CONNECT_ERROR, 'error'))
        # the annotations on the document are still correct
        self.assertTrue(IAnnotations(document)[WS4PMCLIENT_ANNOTATION_KEY] == ['plonemeeting-assembly'])

    def test_displayMeetingDate(self):
        """
          Test the displayMeetingDate method :
          - not date, a '-' is returned
          - a date, a formatted version is returned with hours if hours != '00:00'
        """
        viewlet = PloneMeetingInfosViewlet(self.portal, self.request, None, None)
        viewlet.update()

        # The no meeting date correspond to a date in 1950
        self.assertEqual(viewlet.displayMeetingDate(""), '-')
        self.assertEqual(viewlet.displayMeetingDate(None), '-')
        self.assertEqual(viewlet.displayMeetingDate("2013-06-10"), u'2013-06-10')
        self.assertEqual(viewlet.displayMeetingDate(
            "2013-06-10 (15:30)"), u'2013-06-10 (15:30)'
        )

    def test_render(self):
        """Ensure that we can render the viewlet without any error"""
        self.changeUser('admin')
        document = createDocument(self.portal)
        viewlet = PloneMeetingInfosViewlet(document, self.request, None, None)
        viewlet.update()
        # now send an element to PloneMeeting and check again
        cleanMemoize(self.request, viewlet)
        item = self._sendToPloneMeeting(document)
        render = viewlet.render()
        self.assertTrue("Document title" in render)
        self.assertTrue("PloneMeeting assembly" in render)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testViewlets, prefix='test_'))
    return suite
