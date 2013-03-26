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

import transaction
from AccessControl import Unauthorized
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter

from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY, UNABLE_TO_CONNECT_ERROR, \
    CORRECTLY_SENT_TO_PM_INFO, ALREADY_SENT_TO_PM_ERROR, NO_PROPOSING_GROUP_ERROR
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase, \
    setCorrectSettingsConfig, createDocument, SEND_TO_PM_VIEW_NAME


class testForms(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def test_canNotCallFormIfNotConnected(self):
        """If no valid parameters are defined in the settings, the view is not accessible
           and a relevant message if displayed to the member in portal_messages."""
        # only available to connected users
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, SEND_TO_PM_VIEW_NAME)
        self.changeUser('pmCreator1')
        self.portal.restrictedTraverse(SEND_TO_PM_VIEW_NAME)

    def test_canNotConnectToPloneMeeting(self):
        """If no valid parameters are defined in the settings, the view is not accessible
           and a relevant message if displayed to the member in portal_messages."""
        # only available to connected users
        self.changeUser('pmCreator1')
        view = self.portal.restrictedTraverse(SEND_TO_PM_VIEW_NAME)
        # when we can not connect, a message is displayed to the user
        messages = IStatusMessage(self.request)
        self.assertTrue(len(messages.show()) == 0)
        # call the view
        view()
        self.assertTrue(len(messages.show()) == 1)
        self.assertEquals(messages.show()[0].message, UNABLE_TO_CONNECT_ERROR)

    def test_canNotExecuteWrongAction(self):
        """While calling the view to execute an action, we check if the user can actually
           execute the action regarding the parameters defined in settings.generated_actions."""
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        # build an url that should not be accessible by the user
        # if the url does not correspond to an available wsclient linked action,
        # an Unauthorized is raised.  This make sure the triggered action is
        # available to the user
        self.request.set('URL', document.absolute_url())
        self.request.set('ACTUAL_URL', document.absolute_url() + '/%s' % SEND_TO_PM_VIEW_NAME)
        self.request.set('meetingConfigId', 'wrong-meeting-config-id')
        self.request.form['form.button.Send'] = 'Send'
        view = document.restrictedTraverse(SEND_TO_PM_VIEW_NAME)
        self.assertRaises(Unauthorized, view)

    def test_sendItemToPloneMeeting(self):
        """Test that the item is actually sent to PloneMeeting."""
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        self.request.set('URL', document.absolute_url())
        self.request.set('ACTUAL_URL', document.absolute_url() + '/%s' % SEND_TO_PM_VIEW_NAME)
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        view = document.restrictedTraverse(SEND_TO_PM_VIEW_NAME)
        # before sending, no item is linked to the document
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 0)
        # create the 'pmCreator1' member area to be able to create an item
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created member area...
        transaction.commit()
        # send to PloneMeeting
        # as form.button.Send is not in the form, nothing is done but returning the views's index
        # the form for sending an element is displayed
        form_action = '<form class="rowlike enableUnloadProtection   kssattr-formname-document"' \
            ' action="http://localhost:55001/plone/Members/pmCreator1/document" method="post"' \
            ' id="form" enctype="multipart/form-data">'
        self.assertTrue(form_action in view())
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 0)
        # now send the element to PM
        view.proposingGroupId = 'developers'
        # view._doSendToPloneMeeting returns True if the element was actually sent
        self.assertTrue(view._doSendToPloneMeeting())
        # while the element is sent, the view will return nothing...
        self.assertFalse(view())
        # now that the element has been sent, an item is linked to the document
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)

    def test_canNotSendIfInNoPMCreatorGroup(self):
        """
          If the user that wants to send the item in PloneMeeting is not a creator in PM,
          aka is not in a _creators suffixed group, a message is displayed to him.
        """
        # remove pmCreator2 from the vendors_creators group
        # first check that the user is actually in a _creators group
        pmCreator2 = self.portal.portal_membership.getMemberById('pmCreator2')
        self.assertTrue([group for group in self.portal.acl_users.source_groups.getGroupsForPrincipal(pmCreator2)
                         if group.endswith('_creators')])
        self.portal.portal_groups.removePrincipalFromGroup('pmCreator2', 'vendors_creators')
        # pmCreator2 is no more in a _creators group
        self.assertFalse([group for group in self.portal.acl_users.source_groups.getGroupsForPrincipal(pmCreator2)
                         if group.endswith('_creators')])
        # try to send the item
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator2')
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator2')
        transaction.commit()
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator2)
        messages = IStatusMessage(self.request)
        self.assertFalse(messages.show())
        # if no item is created, _sendToPloneMeeting returns None
        self.assertFalse(self._sendToPloneMeeting(document, user='pmCreator2', proposingGroup='vendors'))
        self.assertTrue(messages.show()[0].message == NO_PROPOSING_GROUP_ERROR % 'pmCreator2')

    def test_checkAlreadySentToPloneMeeting(self):
        """Test in case we sent the element again to PloneMeeting, that should not happen...
           It check also that relevant annotation wipe out works correctly."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        self.request.set('URL', document.absolute_url())
        self.request.set('ACTUAL_URL', document.absolute_url() + '/%s' % SEND_TO_PM_VIEW_NAME)
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        view = document.restrictedTraverse(SEND_TO_PM_VIEW_NAME)
        view.proposingGroupId = 'developers'
        # create the 'pmCreator1' member area to be able to create an item
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created member area...
        transaction.commit()
        # before sending, the element is not linked
        annotations = IAnnotations(document)
        self.assertFalse(WS4PMCLIENT_ANNOTATION_KEY in annotations)
        self.assertFalse(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                                                                           self.request.get('meetingConfigId')))
        # send the document
        self.assertTrue(view._doSendToPloneMeeting())
        # is linked to one item
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == [self.request.get('meetingConfigId'), ])
        self.assertTrue(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                        (self.request.get('meetingConfigId'),)))
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)
        messages = IStatusMessage(self.request)
        # there is one message saying that the item was correctly sent
        shownMessages = messages.show()
        self.assertTrue(len(shownMessages) == 1)
        self.assertEquals(shownMessages[0].message, CORRECTLY_SENT_TO_PM_INFO)
        # call form again, it will display relevant status messages
        # the rendered form is u''
        self.assertTrue(view() == u'')
        # the item is not created again
        # is still linked to one item
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == [self.request.get('meetingConfigId'), ])
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)
        # a warning is displayed to the user
        self.assertTrue(len(messages.show()) == 1)
        self.assertEquals(messages.show()[0].message, ALREADY_SENT_TO_PM_ERROR)
        # if we remove the item in PloneMeeting, the view is aware of it
        itemUID = str(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})[0]['UID'])
        transaction.commit()
        item = self.portal.uid_catalog(UID=itemUID)[0].getObject()
        # remove the item
        item.aq_inner.aq_parent.manage_delObjects(ids=[item.getId(), ])
        transaction.commit()
        # checkAlreadySentToPloneMeeting will wipe out inconsistent annotations
        # for now, annotations are inconsistent
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == [self.request.get('meetingConfigId'), ])
        self.assertFalse(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                        (self.request.get('meetingConfigId'),)))
        # now it is consistent
        self.assertFalse(WS4PMCLIENT_ANNOTATION_KEY in annotations)
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 0)
        # the item can be sent again and will be linked to a new created item
        self.assertTrue(view._doSendToPloneMeeting())
        self.assertTrue(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                        (self.request.get('meetingConfigId'),)))
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)
        # the item can also been send to another meetingConfig
        self.request.set('meetingConfigId', 'plonegov-assembly')
        view = document.restrictedTraverse(SEND_TO_PM_VIEW_NAME)
        view.proposingGroupId = 'developers'
        self.assertFalse(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                        (self.request.get('meetingConfigId'),)))
        self.assertTrue(view._doSendToPloneMeeting())
        self.assertTrue(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                        (self.request.get('meetingConfigId'),)))
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == ['plonemeeting-assembly',
                                                                    self.request.get('meetingConfigId'), ])
        # if we remove the 2 items, a call to checkAlreadySentToPloneMeeting
        # without meetingConfigs will wipeout the annotations
        transaction.commit()
        itemUIDs = [str(elt['UID']) for elt in ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})]

        item1 = self.portal.uid_catalog(UID=itemUIDs[0])[0].getObject()
        item2 = self.portal.uid_catalog(UID=itemUIDs[1])[0].getObject()
        item1.aq_inner.aq_parent.manage_delObjects(ids=[item1.getId(), ])
        item2.aq_inner.aq_parent.manage_delObjects(ids=[item2.getId(), ])
        transaction.commit()
        # annotations are still messed up
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == ['plonemeeting-assembly',
                                                                    self.request.get('meetingConfigId'), ])
        # wipe out annotations
        view.ws4pmSettings.checkAlreadySentToPloneMeeting(document)
        self.assertFalse(WS4PMCLIENT_ANNOTATION_KEY in annotations)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testForms, prefix='test_'))
    return suite
