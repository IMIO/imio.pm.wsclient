# -*- coding: utf-8 -*-
#
# File: testEvents.py
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

from zope.component import getGlobalSiteManager

from imio.pm.wsclient.interfaces import IWillbeSendToPM
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase, \
    setCorrectSettingsConfig, createDocument, SEND_TO_PM_VIEW_NAME

import transaction
import zope


class testEvents(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def test_WillBeSendToPM_event(self):
        """
            Test notification of WillbeSendToPM event when calling _doSendToPloneMeeting.
        """
        event_triggered = False
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        self._configureRequestForView(document)
        view = document.restrictedTraverse(SEND_TO_PM_VIEW_NAME).form_instance
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created member area...
        transaction.commit()
        view.proposingGroupId = 'developers'

        # register a dummy handler for this event
        def will_be_send_to_pm_handler(event):
            event_triggered = True
            return event_triggered
        gsm = getGlobalSiteManager()
        gsm.registerHandler(will_be_send_to_pm_handler, (zope.interface.Interface, IWillbeSendToPM))

        self.assertFalse(event_triggered)
        #send the element to pm
        view._doSendToPloneMeeting()
        self.assertTrue(event_triggered)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testEvents, prefix='test_'))
    return suite
