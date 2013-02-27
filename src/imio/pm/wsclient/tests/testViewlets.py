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

from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase


class testViewlets(WS4PMCLIENTTestCase):
    """
        Tests the browser.testViewlets methods
    """

    def test_xxx(self):
        """"""


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testViewlets, prefix='test_'))
    return suite
