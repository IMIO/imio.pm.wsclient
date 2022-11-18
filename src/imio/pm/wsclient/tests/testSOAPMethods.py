# -*- coding: utf-8 -*-

from datetime import datetime
from imio.pm.ws.config import POD_TEMPLATE_ID_PATTERN
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import cleanMemoize
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase
from plone import api
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import getMultiAdapter


import transaction


class testSOAPMethods(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings SOAP client methods
    """

    def test_rest_connectToPloneMeeting(self):
        """Check that we can actually connect to PloneMeeting with given parameters."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        settings = ws4pmSettings.settings()
        setCorrectSettingsConfig(self.portal, minimal=True)
        # with valid informations, we can connect to PloneMeeting SOAP webservices
        self.failUnless(ws4pmSettings._rest_connectToPloneMeeting())
        # if either url or username/password is not valid, we can not connect...
        valid_url = settings.pm_url
        settings.pm_url = settings.pm_url + 'invalidEndOfURL'
        cleanMemoize(self.request)
        # with invalid url, it fails...
        self.failIf(ws4pmSettings._rest_connectToPloneMeeting())
        settings.pm_url = valid_url
        # with valid url but wrong password, it fails...
        settings.pm_password = u'wrongPassword'
        cleanMemoize(self.request)
        self.failIf(ws4pmSettings._rest_connectToPloneMeeting())

    def test_rest_checkIsLinked(self):
        """Verify that we can get link informations"""
        ws4pmSettings = getMultiAdapter(
            (self.portal, self.request),
            name="ws4pmclient-settings",
        )
        setCorrectSettingsConfig(self.portal, minimal=True)

        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)

        self.changeUser("pmCreator1")
        item1 = self.create("MeetingItem")
        item1.externalIdentifier = "external1"
        item1.reindexObject(idxs=["externalIdentifier", ])
        transaction.commit()

        data = {
            "UID": item1.UID(),
            "externalIdentifier": "external1",
        }
        result = ws4pmSettings._rest_checkIsLinked(data)
        self.assertEqual(item1.UID(), result["UID"])
        self.assertEqual(0, result["extra_include_linked_items_items_total"])

        cfg.setItemManualSentToOtherMCStates(("itemcreated", ))
        self.changeUser("pmCreator2")
        item2 = self.create("MeetingItem", decision="My Decision")
        item2.externalIdentifier = "external2"
        item2.reindexObject(idxs=["externalIdentifier", ])
        self.changeUser("pmManager")
        meeting = self.create("Meeting")
        self.presentItem(item2)
        self.decideMeeting(meeting)
        self.do(item2, "delay")
        transaction.commit()

        item2_link = item2.get_successors()[0]

        data = {
            "UID": item2.UID(),
            "externalIdentifier": "external2",
        }
        result = ws4pmSettings._rest_checkIsLinked(data)
        self.assertEqual(item2.UID(), result["UID"])
        self.assertEqual(1, result["extra_include_linked_items_items_total"])
        self.assertEqual(
            item2_link.UID(),
            result["extra_include_linked_items"][0]["UID"],
        )

    def test_rest_getConfigInfos(self):
        """Check that we receive valid infos about the PloneMeeting's configuration."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        configInfos = ws4pmSettings._rest_getConfigInfos()
        # check that we received meeting config elements
        self.assertTrue(len(configInfos), 2)
        self.assertTrue(configInfos[0]['id'], u'plonemeeting-assembly')
        self.assertTrue(configInfos[1]['id'], u'plonegov-assembly')
        # by default, no categories
        self.assertFalse(configInfos[0].get('categories', False))
        # we can ask categories by passing a showCategories=True to _rest_getConfigInfos
        configInfos = ws4pmSettings._rest_getConfigInfos(showCategories=True)
        self.assertTrue(configInfos[0].get('categories', False))

    def test_rest_getItemCreationAvailableData(self):
        """Check that we receive the list of available data for creating an item."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)

        availableData = ws4pmSettings._rest_getItemCreationAvailableData()
        availableData.sort()
        self.assertEqual(availableData, [u'annexes',
                                         u'associatedGroups',
                                         u'category',
                                         u'decision',
                                         u'description',
                                         u'externalIdentifier',
                                         u'extraAttrs',
                                         u'groupsInCharge',
                                         u'ignore_validation_for',
                                         u'motivation',
                                         u'optionalAdvisers',
                                         u'preferredMeeting',
                                         u'proposingGroup',
                                         u'title',
                                         u'toDiscuss'])

    def test_rest_getItemInfos(self):
        """Check the fact of getting informations about an existing item."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        # by default no item exist in the portal...  So create one!
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        self.assertTrue(len(ws4pmSettings._rest_getItemInfos({'UID': item.UID()})) == 1)
        # getItemInfos is called inTheNameOf the currently connected user
        # if the user (like 'pmCreator1') can see the item, he gets it in the request
        # either (like for 'pmCreator2') the item is not found
        self.changeUser('pmCreator1')
        self.assertTrue(len(ws4pmSettings._rest_getItemInfos({'UID': item.UID()})) == 1)
        self.changeUser('pmCreator2')
        self.assertTrue(len(ws4pmSettings._rest_getItemInfos({'UID': item.UID()})) == 0)

    def test_rest_getUserInfos_groups_and_suffix(self):
        """Test _rest_getUserInfos with group and suffix parameter"""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name="ws4pmclient-settings")
        setCorrectSettingsConfig(self.portal, minimal=True)
        self.changeUser("pmCreator1")

        user_infos = ws4pmSettings._rest_getUserInfos(
            showGroups=True,
            suffix="creators",
        )
        self.assertIsNotNone(user_infos)
        self.assertEqual("pmCreator1", user_infos["id"])
        self.assertEqual(1, user_infos["extra_include_groups_items_total"])
        self.assertEqual("developers", user_infos["extra_include_groups"][0]["id"])

        # Suffix that does not match any group
        user_infos = ws4pmSettings._rest_getUserInfos(
            showGroups=True,
            suffix="observers",
        )
        self.assertIsNotNone(user_infos)
        self.assertEqual("pmCreator1", user_infos["id"])
        self.assertEqual(0, user_infos["extra_include_groups_items_total"])

    def test_rest_getUserInfos_groups_and_wihout_suffix(self):
        """Test _rest_getUserInfos with only group parameter"""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name="ws4pmclient-settings")
        setCorrectSettingsConfig(self.portal, minimal=True)
        self.changeUser("pmCreator1")

        user_infos = ws4pmSettings._rest_getUserInfos(
            showGroups=True,
        )
        self.assertIsNotNone(user_infos)
        self.assertEqual("pmCreator1", user_infos["id"])
        self.assertEqual(1, user_infos["extra_include_groups_items_total"])
        self.assertEqual("developers", user_infos["extra_include_groups"][0]["id"])

    def test_rest_getUserInfos_default(self):
        """Test _rest_getUserInfos with default parameters (no groups or suffix)"""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name="ws4pmclient-settings")
        setCorrectSettingsConfig(self.portal, minimal=True)
        self.changeUser("pmCreator1")

        user_infos = ws4pmSettings._rest_getUserInfos()
        self.assertIsNotNone(user_infos)
        self.assertEqual("pmCreator1", user_infos["id"])
        self.assertTrue("extra_include_groups" not in user_infos)

    def test_rest_searchItems(self):
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
        result = ws4pmSettings._rest_searchItems({'Title': SAME_TITLE})
        self.assertTrue(len(result), 1)
        self.assertTrue(result[0]["UID"] == item1.UID())
        self.changeUser('pmCreator2')
        result = ws4pmSettings._rest_searchItems({'Title': SAME_TITLE})
        self.assertTrue(len(result), 1)
        self.assertTrue(result[0]["UID"] == item2.UID())

    def test_rest_createItem_with_ignore_validation(self):
        """Check item creation with `ignore_validation_for` parameter"""
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        self.changeUser('pmManager')
        self.setMeetingConfig(cfg2Id)
        self._enableField("internalNotes")
        test_meeting = self.create('Meeting')
        self.freezeMeeting(test_meeting)
        self.changeUser('pmCreator1')
        # create the 'pmCreator1' member area to be able to create an item
        pmFolder = self.tool.getPloneMeetingFolder(cfg2Id)
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # create an item for 'pmCreator1'
        data = {'title': u'My sample item',
                'description': u'<p>My description</p>',
                # also use accents, this was failing with suds-jurko 0.5
                'decision': u'<p>My d\xe9cision</p>',
                'preferredMeeting': test_meeting.UID(),
                'externalIdentifier': u'my-external-identifier',
                'extraAttrs': [{'key': 'internalNotes',
                                'value': '<p>Internal notes</p>'}]}
        result = ws4pmSettings._rest_createItem(cfg2Id, 'developers', data)
        self.assertIsNone(result)
        messages = IStatusMessage(self.request)
        self.assertEqual(
            messages.show()[-1].message,
            u"An error occured during the item creation in PloneMeeting! The error "
            "message was : [{'field': 'category', 'message': u'Please select a "
            "category.', 'error': 'ValidationError'}]"
        )

        data["ignore_validation_for"] = "category"
        result = ws4pmSettings._rest_createItem(cfg2Id, 'developers', data)
        # commit again so the item is really created
        transaction.commit()
        # the item is created and his UID is returned
        # check that the item is actually created inTheNameOf 'pmCreator1'
        self.assertIsNotNone(result)
        itemUID = result[0]
        item = self.portal.uid_catalog(UID=itemUID)[0].getObject()
        self.assertTrue(item.aq_inner.aq_parent.UID(), pmFolder.UID())
        self.assertTrue(item.owner_info()['id'] == 'pmCreator1')
        self.assertEqual(item.Title(), data['title'])

    def test_rest_createItem(self):
        """Check item creation.
           Item creation will automatically use currently connected user
           to create the item regarding the _getUserIdToUseInTheNameOfWith."""
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        self.changeUser('pmManager')
        self.setMeetingConfig(cfg2Id)
        self._enableField("internalNotes")
        test_meeting = self.create('Meeting')
        self.freezeMeeting(test_meeting)
        self.changeUser('pmCreator1')
        # create the 'pmCreator1' member area to be able to create an item
        pmFolder = self.tool.getPloneMeetingFolder(cfg2Id)
        # we have to commit() here or portal used behing the SOAP call
        # does not have the freshly created item...
        transaction.commit()
        # create an item for 'pmCreator1'
        data = {'title': u'My sample item',
                'category': u'deployment',
                'description': u'<p>My description</p>',
                # also use accents, this was failing with suds-jurko 0.5
                'decision': u'<p>My d\xe9cision</p>',
                'preferredMeeting': test_meeting.UID(),
                'externalIdentifier': u'my-external-identifier',
                'extraAttrs': [{'key': 'internalNotes',
                                'value': '<p>Internal notes</p>'}]}
        result = ws4pmSettings._rest_createItem(cfg2Id, 'developers', data)
        # commit again so the item is really created
        transaction.commit()
        # the item is created and his UID is returned
        # check that the item is actually created inTheNameOf 'pmCreator1'
        self.assertIsNotNone(result)
        itemUID = result[0]
        item = self.portal.uid_catalog(UID=itemUID)[0].getObject()
        # created in the 'pmCreator1' member area
        self.assertTrue(item.aq_inner.aq_parent.UID(), pmFolder.UID())
        self.assertTrue(item.owner_info()['id'] == 'pmCreator1')
        self.assertEqual(item.Title(), data['title'])
        self.assertEqual(item.getCategory(), data['category'])
        self.assertEqual(item.Description(), data['description'])
        self.assertEqual(item.getDecision(), data['decision'].encode('utf-8'))
        self.assertEqual(item.getPreferredMeeting(), test_meeting.UID(), data['preferredMeeting'])
        self.assertEqual(item.externalIdentifier, data['externalIdentifier'])
        # extraAttrs
        # XXX Does not work ATM, value is always empty
        # self.assertEqual(item.getInternalNotes(), data['internalNotes'])

        # if we try to create with wrong data, the SOAP ws returns a response
        # that is displayed to the user creating the item
        data['category'] = 'unexisting-category-id'
        result = ws4pmSettings._rest_createItem('plonegov-assembly', 'developers', data)
        self.assertIsNone(result)
        messages = IStatusMessage(self.request)
        # a message is displayed
        self.assertEqual(messages.show()[-1].message,
                         u"An error occured during the item creation in PloneMeeting! "
                         "The error message was : [{'field': 'category', 'message': "
                         "u'Please select a category.', 'error': 'ValidationError'}]")

    def test_rest_getItemTemplate(self):
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
        self.assertTrue(ws4pmSettings._rest_getItemTemplate(
            {'itemUID': item.UID(),
             'templateId': POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt')}))
        # getItemTemplate is called inTheNameOf the currently connected user
        # if the user (like 'pmCreator1') can see the item, he gets the rendered template
        # either (like for 'pmCreator2') nothing is returned
        self.changeUser('pmCreator1')
        self.assertTrue(ws4pmSettings._rest_getItemTemplate(
            {'itemUID': item.UID(),
             'templateId': POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt')}))
        self.changeUser('pmCreator2')
        self.assertFalse(ws4pmSettings._rest_getItemTemplate(
            {'itemUID': item.UID(),
             'templateId': POD_TEMPLATE_ID_PATTERN.format('itemTemplate', 'odt')}))

    def test_rest_getMeetingAcceptingItems(self):
        """Check getting accepting items meeting.
           Should only return meetings in the state 'creation' and 'frozen'"""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        meetings = ws4pmSettings._rest_getMeetingsAcceptingItems(
            {'meetingConfigId': cfgId, 'inTheNameOf': 'pmCreator1'}
        )
        self.assertEqual(meetings, [])
        self.changeUser('pmManager')
        meeting_1 = self.create('Meeting', date=datetime(2013, 3, 3))
        meeting_2 = self.create('Meeting', date=datetime(2013, 3, 3))
        transaction.commit()
        self.changeUser('pmCreator1')
        meetings = ws4pmSettings._rest_getMeetingsAcceptingItems(
            {'meetingConfigId': cfgId, 'inTheNameOf': 'pmCreator1'}
        )
        # so far find the two meetings
        self.assertEqual(len(meetings), 2)

        # freeze meeting_2 => it still should be in the accepting items meetings
        self.changeUser('pmManager')
        api.content.transition(meeting_2, 'freeze')
        transaction.commit()
        self.changeUser('pmCreator1')
        meetings = ws4pmSettings._rest_getMeetingsAcceptingItems(
            {'meetingConfigId': cfgId, 'inTheNameOf': 'pmCreator1'}
        )
        self.assertEqual(len(meetings), 2)

        self.changeUser('pmManager')
        api.content.transition(meeting_2, 'publish')
        api.content.transition(meeting_2, 'decide')
        transaction.commit()
        # after publishing meeting_2, it should not be in the results anymore.
        self.changeUser('pmCreator1')
        meetings = ws4pmSettings._rest_getMeetingsAcceptingItems(
            {'meetingConfigId': cfgId, 'inTheNameOf': 'pmCreator1'}
        )
        self.assertEqual(len(meetings), 1)
        self.assertEqual(meetings[0]["UID"], meeting_1.UID())
        # if no inTheNameOf param is explicitly passed, _rest_getMeetingsAcceptingItems()
        # should set a default one.
        meetings = ws4pmSettings._rest_getMeetingsAcceptingItems(
            {'meetingConfigId': cfgId}
        )
        self.assertEqual(len(meetings), 1)
        self.assertEqual(meetings[0]["UID"], meeting_1.UID())

        # As pmManager, we should get all the meetings
        meetings = ws4pmSettings._rest_getMeetingsAcceptingItems(
            {'meetingConfigId': cfgId, 'inTheNameOf': 'pmManager'}
        )
        self.assertEqual(len(meetings), 2)

        # Ensure that meetings have a date
        self.assertEqual("2013-03-03T00:00:00", meetings[0]["date"])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testSOAPMethods, prefix='test_'))
    return suite
