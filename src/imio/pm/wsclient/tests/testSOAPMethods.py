# -*- coding: utf-8 -*-
#
# File: testSOAPMethods.py
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

import transaction
from zope.component import getMultiAdapter

from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.ws.config import POD_TEMPLATE_ID_PATTERN

from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import cleanMemoize
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase


class testSOAPMethods(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def test_soap_connectToPloneMeeting(self):
        """Check that we can actually connect to PloneMeeting with given parameters."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        settings = ws4pmSettings.settings()
        setCorrectSettingsConfig(self.portal, minimal=True)
        # with valid informations, we can connect to PloneMeeting SOAP webservices
        self.failUnless(ws4pmSettings._soap_connectToPloneMeeting())
        # if either url or username/password is not valid, we can not connect...
        valid_url = settings.pm_url
        settings.pm_url = settings.pm_url + 'invalidEndOfURL'
        cleanMemoize(self.request)
        # with invalid url, it fails...
        self.failIf(ws4pmSettings._soap_connectToPloneMeeting())
        settings.pm_url = valid_url
        # with valid url but wrong password, it fails...
        settings.pm_password = u'wrongPassword'
        cleanMemoize(self.request)
        self.failIf(ws4pmSettings._soap_connectToPloneMeeting())

    def test_soap_getConfigInfos(self):
        """Check that we receive valid infos about the PloneMeeting's configuration."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        configInfos = ws4pmSettings._soap_getConfigInfos()
        # check taht we received elements like MeetingConfig and MeetingGroups
        self.assertTrue('MeetingConfig' in [configInfo.type for configInfo in configInfos])
        self.assertTrue('MeetingGroup' in [configInfo.type for configInfo in configInfos])
        # by default, no categories
        self.assertFalse(hasattr(configInfos[0], 'categories'))
        # we can ask categories by passing a showCategories=True to _soap_getConfigInfos
        configInfos = ws4pmSettings._soap_getConfigInfos(showCategories=True)
        self.assertTrue(hasattr(configInfos[0], 'categories'))

    def test_soap_getItemCreationAvailableData(self):
        """Check that we receive the list of available data for creating an item."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        availableData = ws4pmSettings._soap_getItemCreationAvailableData()
        availableData.sort()
        self.assertEquals(availableData, ['annexes',
                                          'category',
                                          'decision',
                                          'description',
                                          'detailedDescription',
                                          'externalIdentifier',
                                          'motivation',
                                          'preferredMeeting',
                                          'proposingGroup',
                                          'title'])

    def test_soap_getItemInfos(self):
        """Check the fact of getting informations about an existing item."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        # by default no item exist in the portal...  So create one!
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        self.assertTrue(len(ws4pmSettings._soap_getItemInfos({'UID': item.UID()})) == 1)
        # getItemInfos is called inTheNameOf the currently connected user
        # if the user (like 'pmCreator1') can see the item, he gets it in the request
        # either (like for 'pmCreator2') the item is not found
        self.changeUser('pmCreator1')
        self.assertTrue(len(ws4pmSettings._soap_getItemInfos({'UID': item.UID()})) == 1)
        self.changeUser('pmCreator2')
        self.assertTrue(len(ws4pmSettings._soap_getItemInfos({'UID': item.UID()})) == 0)

    def test_soap_searchItems(self):
        """Check the fact of searching items informations about existing items."""
        SAME_TITLE = 'sameTitleForBothItems'
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        # Create 2 items, one for 'pmCreator1' and one for 'pmCreator2'
        # items are only viewable by their creator as 'pmCreatorx' not in the same proposingGroup
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setTitle(SAME_TITLE)
        item1.reindexObject(idxs=['Title', ])
        self.changeUser('pmCreator2')
        item2 = self.create('MeetingItem')
        item2.setTitle(SAME_TITLE)
        item2.reindexObject(idxs=['Title', ])
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # searchItems will automatically restrict searches to the connected user
        self.changeUser('pmCreator1')
        result = ws4pmSettings._soap_searchItems({'Title': SAME_TITLE})
        self.assertTrue(len(result), 1)
        self.assertTrue(result[0].UID == item1.UID())
        self.changeUser('pmCreator2')
        result = ws4pmSettings._soap_searchItems({'Title': SAME_TITLE})
        self.assertTrue(len(result), 1)
        self.assertTrue(result[0].UID == item2.UID())

    def test_soap_createItem(self):
        """Check item creation.
           Item creation will automatically use currently connected user
           to create the item regarding the _getUserIdToUseInTheNameOfWith."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        self.changeUser('pmCreator1')
        # create the 'pmCreator1' member area to be able to create an item
        pmFolder = self.tool.getPloneMeetingFolder('plonegov-assembly', 'pmCreator1')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # create an item for 'pmCreator1'
        data = {'title': u'My sample item',
                'category': u'deployment',
                'description': u'<p>My description</p>',
                # also use accents, this was failing with suds-jurko 0.5
                'decision': u'<p>My d\xe9cision</p>',
                'externalIdentifier': u'my-external-identifier'}
        result = ws4pmSettings._soap_createItem('plonegov-assembly', 'developers', data)
        # commit again so the item is really created
        transaction.commit()
        # the item is created and his UID is returned
        # check that the item is actually created inTheNameOf 'pmCreator1'
        itemUID = result[0]
        item = self.portal.uid_catalog(UID=itemUID)[0].getObject()
        # created in the 'pmCreator1' member area
        self.assertTrue(item.aq_inner.aq_parent.UID(), pmFolder.UID())
        self.assertTrue(item.owner_info()['id'] == 'pmCreator1')
        # if we try to create with wrong data, the SOAP ws returns a response
        # that is displayed to the user creating the item
        data['category'] = 'unexisting-category-id'
        result = ws4pmSettings._soap_createItem('plonegov-assembly', 'developers', data)
        self.assertTrue(result is None)
        messages = IStatusMessage(self.request)
        # a message is displayed
        self.assertEquals(messages.show()[-1].message,
                          u"An error occured during the item creation in PloneMeeting! "
                          "The error message was : Server raised fault: ''unexisting-category-id' "
                          "is not available for the 'developers' group!'")

    def test_soap_getItemTemplate(self):
        """Check while getting rendered template for an item.
           getItemTemplate will automatically use currently connected user
           to render item template regarding the _getUserIdToUseInTheNameOfWith."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        # by default no item exist in the portal...  So create one!
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        self.assertTrue(ws4pmSettings._soap_getItemTemplate(
            {'itemUID': item.UID(),
             'templateId': POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt')}))
        # getItemTemplate is called inTheNameOf the currently connected user
        # if the user (like 'pmCreator1') can see the item, he gets the rendered template
        # either (like for 'pmCreator2') nothing is returned
        self.changeUser('pmCreator1')
        self.assertTrue(ws4pmSettings._soap_getItemTemplate(
            {'itemUID': item.UID(),
             'templateId': POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt')}))
        self.changeUser('pmCreator2')
        self.assertFalse(ws4pmSettings._soap_getItemTemplate(
            {'itemUID': item.UID(),
             'templateId': POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt')}))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testSOAPMethods, prefix='test_'))
    return suite
