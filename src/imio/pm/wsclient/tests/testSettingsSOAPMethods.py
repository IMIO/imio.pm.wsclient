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

from zope.component import getMultiAdapter
from zope.annotation.interfaces import IAnnotations

from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase, setCorrectSettingsConfig


class testSettingsSOAPMethods(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def test_soap_connectToPloneMeeting(self):
        """Check that we can actually connect to PloneMeeting with given parameters."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        settings = ws4pmSettings.settings()
        setCorrectSettingsConfig(self.portal, settings, minimal=True)
        # with valid informations, we can connect to PloneMeeting SOAP webservices
        self.failUnless(ws4pmSettings._soap_connectToPloneMeeting())
        # if either url or username/password is not valid, we can not connect...
        settings.pm_url = settings.pm_url + 'invalidEndOfURL'
        self._cleanMemoizeOnSOAPMethods()
        self.failIf(ws4pmSettings._soap_connectToPloneMeeting())
        settings.pm_url = settings.pm_url.rstrip('invalidEndOfURL')
        settings.pm_password = u'wrongPassword'
        self._cleanMemoizeOnSOAPMethods()
        self.failIf(ws4pmSettings._soap_connectToPloneMeeting())

    def _cleanMemoizeOnSOAPMethods(self):
        """SOAP methods are memoized, making it impossible to test twice...
           So clean memoized informations so the called
           SOAP method is really rendered again..."""
        annotations = IAnnotations(self.request)
        annotations['plone.memoize'].clear()


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testSettingsSOAPMethods, prefix='test_'))
    return suite
