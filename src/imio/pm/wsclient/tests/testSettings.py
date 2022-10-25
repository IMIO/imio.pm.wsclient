# -*- coding: utf-8 -*-
#
# File: testItemMethods.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.pm.wsclient.config import ACTION_SUFFIX
from imio.pm.wsclient.testing import WS4PMCLIENT_PM_TESTING_PROFILE_FUNCTIONAL
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import createDocument
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing.interfaces import TEST_USER_ID
from plone.app.testing.interfaces import TEST_USER_NAME
from zope.component import getMultiAdapter
from zope.event import notify
from zope.tales.tales import CompilerError
from zope.traversing.interfaces import BeforeTraverseEvent

import unittest


class testSettings(unittest.TestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    layer = WS4PMCLIENT_PM_TESTING_PROFILE_FUNCTIONAL

    def setUp(self):
        portal = self.layer['portal']
        request = self.layer['request']
        self.portal = portal
        self.request = request
        # setup manually the correct browserlayer, see:
        # https://dev.plone.org/ticket/11673
        notify(BeforeTraverseEvent(self.portal, self.request))

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
        self.assertEquals(fields, ['allowed_annexes_types',
                                   'field_mappings',
                                   'generated_actions',
                                   'only_one_sending',
                                   'pm_password',
                                   'pm_timeout',
                                   'pm_url',
                                   'pm_username',
                                   'user_mappings',
                                   'viewlet_display_condition'])

    def test_saveSettings(self):
        """While settings are saved, some actions are added to portal_actions/object_buttons."""
        setRoles(self.portal, TEST_USER_ID, ('Manager',))
        login(self.portal, TEST_USER_NAME)
        # for now, there are no relative plonemeeting actions in portal_actions/object_buttons
        object_buttons_ids = self.portal.portal_actions.object_buttons.objectIds()
        self.failIf([actId for actId in object_buttons_ids if actId.startswith(ACTION_SUFFIX)])
        setCorrectSettingsConfig(self.portal, withValidation=False)
        # now relevant actions exist
        object_buttons_ids = self.portal.portal_actions.object_buttons.objectIds()
        self.assertEquals(len([actId for actId in object_buttons_ids if actId.startswith(ACTION_SUFFIX)]), 5)
        # and it is correctly configured
        setRoles(self.portal, TEST_USER_ID, ('Member',))
        # plone.app.testing does not manage request/URL and request/ACTUAL_URL
        # and request/ACTUAL_URL is necessary for listFilteredActionsFor
        self.request.set('URL', self.portal.absolute_url())
        self.request.set('ACTUAL_URL', self.portal.absolute_url())
        object_buttons = self.portal.portal_actions.listFilteredActionsFor(self.portal)['object_buttons']
        # 2 of the generated actions are not available to non 'Managers'
        self.assertEquals(len([act for act in object_buttons if act['id'].startswith(ACTION_SUFFIX)]), 5 - 2)
        # now save again with just 2 actions to generate
        generated_actions = [
            {'pm_meeting_config_id': 'plonegov-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
            {'pm_meeting_config_id': 'plonemeeting-assembly',
             'condition': u'python:True',
             'permissions': u'View'},
        ]
        setCorrectSettingsConfig(self.portal,
                                 withValidation=False,
                                 **{'generated_actions': generated_actions})
        object_buttons = self.portal.portal_actions.listFilteredActionsFor(self.portal)['object_buttons']
        pm_object_buttons = [act for act in object_buttons if act['id'].startswith(ACTION_SUFFIX)]
        # only 2 actions exist now
        self.assertEquals(len(pm_object_buttons), 2)
        # and it is valid ones
        self.assertTrue('meetingConfigId=plonegov-assembly' in pm_object_buttons[0]['url'])
        self.assertTrue('meetingConfigId=plonemeeting-assembly' in pm_object_buttons[1]['url'])

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
        settings.user_mappings = [{'local_userid': u'localUserId',
                                   'pm_userid': u'pmCreator1'},
                                  {'local_userid': u'lambda',
                                   'pm_userid': u'aUserInPloneMeeting'},
                                  {'local_userid': u'admin',
                                   'pm_userid': u'pmCreator1'}, ]
        login(self.portal, 'lambda')
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), u'aUserInPloneMeeting')
        # not the user_mappings is linking to the settings.pm_username
        settings.user_mappings = [{'local_userid': u'localUserId',
                                   'pm_userid': u'pmCreator1'},
                                  {'local_userid': u'lambda',
                                   'pm_userid': u'%s' % TEST_USER_ID},
                                  {'local_userid': u'admin',
                                   'pm_userid': u'pmCreator1'}, ]
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), None)
        # if the user is not the settings.pm_username and not found in the mappings
        # it is his own userId that will be used
        settings.user_mappings = [{'local_userid': u'localUserId',
                                   'pm_userid': u'pmCreator1'},
                                  {'local_userid': u'otherUser',
                                   'pm_userid': u'otherUserInPloneMeeting'},
                                  {'local_userid': u'admin',
                                   'pm_userid': u'pmCreator1'}, ]
        self.assertEquals(ws4pmSettings._getUserIdToUseInTheNameOfWith(), 'lambda')

    def test_renderTALExpression(self):
        """
          Test the method that will render a TAL expression
        """
        setRoles(self.portal, TEST_USER_ID, ('Manager',))
        login(self.portal, TEST_USER_NAME)
        # create an element to use in the TAL expression...
        document = createDocument(self.portal)
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        expr = u'python: None'
        # make sure None is never returned by the renderer as it breaks SOAP calls
        self.assertTrue(ws4pmSettings.renderTALExpression(document, self.portal, expr, {}) == u'')
        expr = u'object/Title'
        self.assertTrue(ws4pmSettings.renderTALExpression(document, self.portal, expr, {}) == u'Document title')
        expr = u'string:"My expr result"'
        self.assertTrue(ws4pmSettings.renderTALExpression(document, self.portal, expr, {}) == u'"My expr result"')
        # with a wrong expression, we raise
        expr = 'u object/wrongMethodCall'
        self.assertRaises(CompilerError, ws4pmSettings.renderTALExpression, document, self.portal, expr, {})


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSettings))
    return suite
