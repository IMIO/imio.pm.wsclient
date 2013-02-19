# -*- coding: utf-8 -*-
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

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from imio.pm.ws.testing import WS4PM_PM_TEST_PROFILE_FUNCTIONAL

class WS4PMTestCase(PloneMeetingTestCase):
    '''Base class for defining WS4PM test cases.'''

    layer = WS4PM_PM_TEST_PROFILE_FUNCTIONAL

    def setUp(self):
        """ """
        PloneMeetingTestCase.setUp(self)


from lxml import etree
from ZSI import SoapWriter, TC

def serializeRequest(request):
    tc = getattr(request, 'typecode', None)
    sw = SoapWriter(nsdict={}, header=True, outputclass=None,
                    encodingStyle=None)
    return str(sw.serialize(request, tc))


def deserialize(objectToDeserialize):
    sw = SoapWriter(nsdict={}, header=True, outputclass=None,
                    encodingStyle=None)
    tc = TC.Any(pname=None, aslist=False)
    deserializedObject = sw.serialize(objectToDeserialize, tc).body
    root = etree.XML(str(deserializedObject))
    body = root[0]
    return etree.tostring(body, encoding='utf-8', pretty_print=True)