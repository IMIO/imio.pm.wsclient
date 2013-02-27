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

import unittest2
from plone.app.testing.interfaces import TEST_USER_ID, TEST_USER_NAME
from plone.app.testing import login, setRoles

from AccessControl import Unauthorized
from zope.component import getMultiAdapter

from imio.pm.wsclient.config import ACTION_SUFFIX
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from imio.pm.wsclient.testing import WS4PMCLIENT_PROFILE_FUNCTIONAL


class testSettings(unittest2.TestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    layer = WS4PMCLIENT_PROFILE_FUNCTIONAL

    def setUp(self):
        portal = self.layer['portal']
        request = self.layer['request']
        self.portal = portal
        self.request = request

    def test_ws4pmSettings(self):
        """Check that we can actually access settings and that we have the correct fields."""
        # settings are only available to connected users having "Manage portal" permission
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, '@@ws4pmclient-settings')
        login(self.portal, TEST_USER_NAME)
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, '@@ws4pmclient-settings')
        setRoles(self.portal, TEST_USER_ID, ('Manager',))
        ws4pmSettings = self.portal.restrictedTraverse('@@ws4pmclient-settings')
        settings = ws4pmSettings.settings()
        fields = settings.__schema__._InterfaceClass__attrs.keys()
        fields.sort()
        self.assertEquals(fields, ['field_mappings',
                                   'generated_actions',
                                   'pm_password',
                                   'pm_url',
                                   'pm_username',
                                   'user_mappings',
                                   'viewlet_display_condition'])

    def test_saveSettings(self):
        """While settings are saved, some actions are added to portal_actions/object_buttons."""
        setRoles(self.portal, TEST_USER_ID, ('Manager',))
        login(self.portal, TEST_USER_NAME)
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        settings = ws4pmSettings.settings()
        # for now, there are no relative plonemeeting actions in portal_actions/object_buttons
        object_buttons_ids = self.portal.portal_actions.object_buttons.objectIds()
        self.failIf([actId for actId in object_buttons_ids if actId.startswith(ACTION_SUFFIX)])
        setCorrectSettingsConfig(self.portal, settings, withValidation=False)
        # now relevant actions exist
        number_actions_to_generated = len(settings.generated_actions)
        object_buttons_ids = self.portal.portal_actions.object_buttons.objectIds()
        self.assertEquals(len([actId for actId in object_buttons_ids if actId.startswith(ACTION_SUFFIX)]),
                          number_actions_to_generated)
        # and it is correctly configured
        setRoles(self.portal, TEST_USER_ID, ('Member',))
        # plone.app.testing does not manage request/URL and request/ACTUAL_URL
        # and request/ACTUAL_URL is necessary for listFilteredActionsFor
        self.request.set('URL', self.portal.absolute_url())
        self.request.set('ACTUAL_URL', self.portal.absolute_url())
        object_buttons = self.portal.portal_actions.listFilteredActionsFor(self.portal)['object_buttons']
        # 2 of the generated actions are not available to non 'Managers'
        self.assertEquals(len([act for act in object_buttons if act['id'].startswith(ACTION_SUFFIX)]),
                          number_actions_to_generated - 2)

    def test_getUserIdToUseInTheNameOfWith(self):
        """Returns the userId that will actually create the item.
           Returns None if we found out that it is the defined settings.pm_username
           that will create the item : either it is the currently connected user,
           or there is an existing user_mapping between currently connected user
           and settings.pm_username user. """
        setRoles(self.portal, TEST_USER_ID, ('Manager',))
        login(self.portal, TEST_USER_NAME)
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        # this method is taking care of values in settings.pm_username
        # and settings.user_mappings
        # first define no user_mappings and no pm_username,
        # the currently logged in user will be the creator
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), TEST_USER_ID)
        # check that if current member is settings.pm_username, None is returned
        settings = ws4pmSettings.settings()
        settings.pm_username = unicode(TEST_USER_ID, 'utf-8')
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), None)
        # now define user_mappings
        # add a lamba user to be able to test
        self.portal.acl_users.userFolderAddUser('lambda', 'lambda', ['Member'], [])
        # if the found user_mappings leads to a user that is not
        # settings.pm_username, this user mapping is returned
        settings.user_mappings = u'localUserId|pmCreator1\r\nlambda|aUserInPloneMeeting\r\nadmin|pmCreator1'
        login(self.portal, 'lambda')
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), u'aUserInPloneMeeting')
        # not the user_mappings is linking to the settings.pm_username
        settings.user_mappings = u'localUserId|pmCreator1\r\nlambda|%s\r\nadmin|pmCreator1' % TEST_USER_ID
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), None)
        # if the user is not the settings.pm_username and not found in the mappings
        # it is his own userId that will be used
        settings.user_mappings = u'localUserId|pmCreator1\r\notherUser|otherUserInPloneMeeting\r\nadmin|pmCreator1'
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), 'lambda')

    def test_renderTALExpression(self):
        """
          Test the method that will render a TAL expression
        """
        setRoles(self.portal, TEST_USER_ID, ('Manager',))
        login(self.portal, TEST_USER_NAME)
        # create an element to use in the TAL expression...
        data = {'title': 'Document title',
                'description': 'Document description',
                'text': '<p>Document rich text</p>'}
        documentId = self.portal.invokeFactory('Document', id='document', **data)
        document = getattr(self.portal, documentId)
        document.reindexObject()
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        expr = u'python: None'
        # make sure None is never returned by the renderer as it breaks SOAP calls
        self.assertTrue(ws4pmSettings.renderTALExpression(document, self.portal, expr, '') == u'')
        expr = u'object/Title'
        self.assertTrue(ws4pmSettings.renderTALExpression(document, self.portal, expr, '') == u'Document title')
        expr = u'string:"My expr result"'
        self.assertTrue(ws4pmSettings.renderTALExpression(document, self.portal, expr, '') == u'"My expr result"')
        import ipdb; ipdb.set_trace()
        # with a wrong expression, we raise
        expr = 'u '


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSettings))
    return suite
