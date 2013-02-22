# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by Imio.be
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
from imio.pm.wsclient.testing import WS4PMCLIENT_PM_TEST_PROFILE_FUNCTIONAL


class WS4PMCLIENTTestCase(PloneMeetingTestCase):
    '''Base class for defining WS4PMCLIENT test cases.'''

    layer = WS4PMCLIENT_PM_TEST_PROFILE_FUNCTIONAL

    def setUp(self):
        """ """
        PloneMeetingTestCase.setUp(self)


def setCorrectSettingsConfig(portal, settings, minimal=False, withValidation=True):
    """Set a workable set of settings for tests.
       If p_withValidation is False, remove validation because we want
       to force to set some values and relevant vocabularies for example do not contain that value.
       If p_minimal is True, only minimal settings are set to be able to connect."""
    if not withValidation:
        # disable validation when forcing some values to set
        from zope.schema._field import AbstractCollection
        old_validate = AbstractCollection._validate

        def _validate(self, value):
            return
        AbstractCollection._validate = _validate
    settings.pm_url = u'%s/ws4pm.wsdl' % portal.absolute_url()
    settings.pm_username = u'pmManager'
    settings.pm_password = u'meeting'
    settings.user_mappings = u'localUserId|pmCreator1\r\nlocalUserId2|pmCreator2\r\nadmin|pmCreator1'
    if not minimal:
        # these parameters are only available while correctly connected
        # to PloneMeeting webservices, either use withValidation=False
        # these fields mappings make it work if classic Document content_type
        settings.field_mappings = [{'field_name': u'title', 'expression': u'object/Title'},
            {'field_name': u'description', 'expression': u'object/Description'},
            {'field_name': u'category', 'expression': u'string:"deployment"'},
            {'field_name': u'decision', 'expression': u'object/getText'},
            {'field_name': u'externalIdentifier', 'expression': u'object/UID'}]
        settings.generated_actions = [
            {'pm_proposing_group_id': u'developers',
             'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'vendors',
             'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'developers',
             'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'vendors',
             'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:False',
             'permissions': u'View'},
            {'pm_proposing_group_id': u'vendors',
             'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'Manage portal'},
            ]
    if not withValidation:
        AbstractCollection._validate = old_validate
