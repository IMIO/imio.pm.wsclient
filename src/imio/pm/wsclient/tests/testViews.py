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

from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase, \
                                                       setCorrectSettingsConfig, \
                                                       createDocument


class testViews(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def test_canNotConnectToPloneMeeting(self):
        """If no valid parameters are defined in the settings, the view is not accessible
           and a relevant message if displayed to the member in portal_messages."""
        # only available to connected users
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, '@@send_to_plonemeeting')
        self.changeUser('pmCreator1')
        view = self.portal.restrictedTraverse('@@send_to_plonemeeting')
        # when we can not connect, a message is displayed to the user
        messages = IStatusMessage(self.request)
        self.assertTrue(len(messages.show()) == 0)
        # call the view
        view()
        self.assertTrue(len(messages.show()) == 1)
        self.assertEquals(messages.show()[0].message,
                          "Unable to connect to PloneMeeting, check the 'WS4PM Client settings'! "\
                          "Please contact system administrator!")

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
        self.request.set('ACTUAL_URL', document.absolute_url() + '/@@send_to_plonemeeting')
        self.request.set('QUERY_STRING',
                         'meetingConfigId=plonemeeting-assembly&proposingGroupId=anUnexistingProposingGroup')
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        self.request.set('proposingGroupId', 'anUnexistingProposingGroup')
        view = document.restrictedTraverse('@@send_to_plonemeeting')
        self.assertRaises(Unauthorized, view)

    def test_sendItemToPloneMeeting(self):
        """Test that the item is actually sent to PloneMeeting."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        self.request.set('URL', document.absolute_url())
        self.request.set('ACTUAL_URL', document.absolute_url() + '/@@send_to_plonemeeting')
        self.request.set('QUERY_STRING', 'meetingConfigId=plonemeeting-assembly&proposingGroupId=developers')
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        self.request.set('proposingGroupId', 'developers')
        view = document.restrictedTraverse('@@send_to_plonemeeting')
        # before sending, no item is linked to the document
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 0)
        # create the 'pmCreator1' member area to be able to create an item
        self.tool.getPloneMeetingFolder('plonemeeting-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created member area...
        transaction.commit()
        # send to PloneMeeting
        view()
        # now that the element has been sent, an item is linked to the document
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)

    def test_checkAlreadySentToPloneMeeting(self):
        """Test in case we sent the element again to PloneMeeting, that should not happen...
           It check also that relevant annotation wipe out works correctly."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal)
        self.changeUser('pmCreator1')
        # create an element to send...
        document = createDocument(self.portal.Members.pmCreator1)
        self.request.set('URL', document.absolute_url())
        self.request.set('ACTUAL_URL', document.absolute_url() + '/@@send_to_plonemeeting')
        self.request.set('QUERY_STRING', 'meetingConfigId=plonemeeting-assembly&proposingGroupId=developers')
        self.request.set('meetingConfigId', 'plonemeeting-assembly')
        self.request.set('proposingGroupId', 'developers')
        view = document.restrictedTraverse('@@send_to_plonemeeting')
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
        view()
        transaction.commit()
        # is linked to one item
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == [self.request.get('meetingConfigId'), ])
        self.assertTrue(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                                                                            (self.request.get('meetingConfigId'),)))
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)
        messages = IStatusMessage(self.request)
        # there is one message saying that the item was correctly sent
        self.assertTrue(len(messages.show()) == 1)
        self.assertEquals(messages.show()[0].message, u"The item has been correctly sent to PloneMeeting.")
        # send again
        view()
        # the item is not created again
        # is still linked to one item
        self.assertTrue(annotations[WS4PMCLIENT_ANNOTATION_KEY] == [self.request.get('meetingConfigId'), ])
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)
        # a warning is displayed to the user
        self.assertTrue(len(messages.show()) == 2)
        self.assertEquals(messages.show()[1].message, u"This element has already been sent to PloneMeeting!")
        # if we remove the item in PloneMeeting, the view is aware of it
        itemUID = ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})[0]['UID']
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
        view()
        self.assertTrue(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                                                                            (self.request.get('meetingConfigId'),)))
        self.assertTrue(len(ws4pmSettings._soap_searchItems({'externalIdentifier': document.UID()})) == 1)
        # the item can also been send to another meetingConfig
        self.request.set('meetingConfigId', 'plonegov-assembly')
        view = document.restrictedTraverse('@@send_to_plonemeeting')
        self.assertFalse(view.ws4pmSettings.checkAlreadySentToPloneMeeting(document,
                                                                            (self.request.get('meetingConfigId'),)))
        view()
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
    suite.addTest(makeSuite(testViews, prefix='test_'))
    return suite