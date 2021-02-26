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

from imio.pm.wsclient.interfaces import ISentToPMEvent
from imio.pm.wsclient.interfaces import IWillbeSendToPMEvent
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import createDocument
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import SEND_TO_PM_VIEW_NAME
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase
from zope.component import getGlobalSiteManager
from zope.interface import Interface

import transaction


class FailTest(Exception):
    """ Raised when the ws event is not notified at the right moment """


class testEvents(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def setUp(self):
        """
           Set a ws sending view.
        """
        super(testEvents, self).setUp()
        self.sending_view = self._setup_sending_view()

    def test_WillBeSendToPM_event(self):
        """
            Test notification of WillbeSendToPM event when calling _doSendToPloneMeeting.
        """
        sending_view = self.sending_view

        # register a handler raising a dummy exception for this event
        class WillBeSendToPm(Exception):
            """ """
        def will_be_send_to_pm_handler(obj, event):
            if not sending_view._finishedSent:
                raise WillBeSendToPm
            raise FailTest("the WillBeSendToPm event should be raised before sending the item to PM")

        gsm = getGlobalSiteManager()
        gsm.registerHandler(will_be_send_to_pm_handler, (Interface, IWillbeSendToPMEvent))

        # send the element to pm, the event handler should raise the exception
        with self.assertRaises(WillBeSendToPm):
            self.sending_view._doSendToPloneMeeting()

        gsm.unregisterHandler(will_be_send_to_pm_handler, (Interface, IWillbeSendToPMEvent))

    def test_SentToPM_event(self):
        """
            Test notification of SentToPM event when calling _doSendToPloneMeeting.
        """
        sending_view = self.sending_view

        # register a handler raising a dummy exception for this event
        class SentToPm(Exception):
            """ """
        def sent_to_pm_handler(obj, event):
            if sending_view._finishedSent:
                raise SentToPm
            raise FailTest("the SentToPm event should be raised after sending the item to PM")

        gsm = getGlobalSiteManager()
        gsm.registerHandler(sent_to_pm_handler, (Interface, ISentToPMEvent))

        #send the element to pm, the event handler should raise the exception
        with self.assertRaises(SentToPm):
            self.sending_view._doSendToPloneMeeting()

        gsm.unregisterHandler(sent_to_pm_handler, (Interface, ISentToPMEvent))

    def _setup_sending_view(self):
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        self.request.set('URL', document.absolute_url())
        self.request.set('ACTUAL_URL', document.absolute_url() + '/%s' % SEND_TO_PM_VIEW_NAME)
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        view = document.restrictedTraverse(SEND_TO_PM_VIEW_NAME).form_instance
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created member area...
        transaction.commit()
        view.proposingGroupId = 'developers'
        return view


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testEvents, prefix='test_'))
    return suite
