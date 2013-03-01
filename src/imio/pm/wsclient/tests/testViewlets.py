# -*- coding: utf-8 -*-
#
# File: testViewlets.py
#
# Copyright (c) 2013 by Imio
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

from datetime import datetime
import transaction
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient.browser.viewlets import PloneMeetingInfosViewlet
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase, \
                                                       createDocument, \
                                                       cleanMemoize, \
                                                       setCorrectSettingsConfig


class testViewlets(WS4PMCLIENTTestCase):
    """
        Tests the browser.testViewlets methods
    """

    def test_available(self):
        """"""
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
        item = self._sendToPloneMeeting(document, viewlet)
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
        self.assertTrue(len(messages.show()) == 2)
        self.assertTrue(messages.show()[0].message, u'The item has been correctly sent to PloneMeeting.')
        self.assertTrue(messages.show()[1].message, u'There was NO WARNING message during item creation.')
        settings.viewlet_display_condition = u'python: object.getUnexistingAttribute()'
        self.assertFalse(viewlet.available())
        cleanMemoize(self.request, viewlet)
        # one supplementary message
        self.assertEquals(messages.show()[2].message,
                    u'Unable to display informations about the potentially linked item in PloneMeeting because ' \
                    'there was an error evaluating the TAL expression \'python: object.getUnexistingAttribute()\' ' \
                    'for the field \'viewlet_display_condition\'!  The error was : \'getUnexistingAttribute\'.  ' \
                    'Please contact system administrator.')
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
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos() == {})
        # now send an element to PloneMeeting and check again
        cleanMemoize(self.request, viewlet)
        item = self._sendToPloneMeeting(document, viewlet)
        # we received informations about the created item
        self.assertTrue(viewlet.getPloneMeetingLinkedInfos()[0]['UID'] == item.UID())

    def test_displayMeetingDate(self):
        """
          Test the displayMeetingDate method :
          - not date, a '-' is returned
          - a date, a formatted version is returned with hours if hours != '00:00'
        """
        viewlet = PloneMeetingInfosViewlet(self.portal, self.request, None, None)
        viewlet.update()
        # The no meeting date correspond to a date in 1950
        self.assertTrue(viewlet.displayMeetingDate(datetime(1950, 1, 1)) == '-')
        # If there is a date, it is corretly displayed
        # if no hours (hours = 00:00), a short format is used, without displaying hours
        self.assertTrue(viewlet.displayMeetingDate(datetime(2013, 6, 10)) == u'Jun 10, 2013')
        # If hours, then a long format is used
        self.assertTrue(viewlet.displayMeetingDate(datetime(2013, 6, 10, 15, 30)) == u'Jun 10, 2013 03:30 PM')

    def _sendToPloneMeeting(self, obj, viewlet):
        """
          Helper method for sending an element to PloneMeeting
        """
        # set correct config
        setCorrectSettingsConfig(self.portal)
        # create the 'pmCreator1' member area to be able to create an item
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # use the 'send_to_plonemeeting' view
        self.request.set('URL', obj.absolute_url())
        self.request.set('ACTUAL_URL', obj.absolute_url() + '/@@send_to_plonemeeting')
        self.request.set('QUERY_STRING', 'meetingConfigId=plonemeeting-assembly&proposingGroupId=developers')
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        self.request.set('proposingGroupId', 'developers')
        obj.restrictedTraverse('@@send_to_plonemeeting')()
        transaction.commit()
        return self.portal.portal_catalog(portal_type='MeetingItemPma', Title=obj.Title())[0].getObject()


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testViewlets, prefix='test_'))
    return suite
