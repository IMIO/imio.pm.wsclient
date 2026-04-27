# -*- coding: utf-8 -*-

from datetime import datetime
from imio.pm.ws.config import POD_TEMPLATE_ID_PATTERN
from imio.pm.wsclient.config import CONFIG_UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import cleanMemoize
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import setCorrectSettingsConfig
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase
from mock import MagicMock
from mock import patch
from plone import api
from Products.Archetypes.event import ObjectEditedEvent
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import getMultiAdapter
from zope.event import notify

import requests as requests_module
import transaction


class testRESTMethods(WS4PMCLIENTTestCase):
    """
        Tests the browser.settings REST client methods
    """

    def setUp(self):
        super(testRESTMethods, self).setUp()
        IStatusMessage(self.request).show()  # drain messages added by test env setup

    def test_rest_connectToPloneMeeting(self):
        """Check that _rest_connectToPloneMeeting returns a session when configured and None when not.
        """
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        settings = ws4pmSettings.settings()
        setCorrectSettingsConfig(self.portal, minimal=True)
        # with valid settings, an authenticated session is returned
        session = ws4pmSettings._rest_connectToPloneMeeting()
        self.assertIsInstance(session, requests_module.Session)
        self.assertEqual(session.auth[0], settings.pm_username)
        # not configured: empty url returns None
        valid_url = settings.pm_url
        settings.pm_url = u''
        cleanMemoize(self.request)
        self.assertIsNone(ws4pmSettings._rest_connectToPloneMeeting())
        # not configured: empty username returns None
        settings.pm_url = valid_url
        valid_username = settings.pm_username
        settings.pm_username = u''
        cleanMemoize(self.request)
        self.assertIsNone(ws4pmSettings._rest_connectToPloneMeeting())
        # not configured: empty password returns None
        settings.pm_username = valid_username
        settings.pm_password = u''
        cleanMemoize(self.request)
        self.assertIsNone(ws4pmSettings._rest_connectToPloneMeeting())

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
            "externalIdentifier": "external1",
        }
        result = ws4pmSettings._rest_checkIsLinked(data)
        self.assertEqual(item1.UID(), result["UID"])
        # self.assertEqual(0, result.get("extra_include_linked_items_items_total", 0))

        cfg.setItemManualSentToOtherMCStates(("itemcreated", ))
        self.changeUser("pmCreator2")
        result = ws4pmSettings._rest_checkIsLinked({"externalIdentifier": "external1"})
        self.assertTrue(result)  # 403
        result = ws4pmSettings._rest_checkIsLinked({"externalIdentifier": "unexisting-external-id"})
        self.assertFalse(result)  # 404

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
        # plonemeeting-assembly has no categories BTW, so we use plonegov-assembly
        self.assertFalse(configInfos[1].get('categories', False))
        # we can ask categories by passing a showCategories=True to _rest_getConfigInfos
        configInfos = ws4pmSettings._rest_getConfigInfos(showCategories=True)
        self.assertEqual(len(configInfos[1].get('categories')), 6)

    def test_rest_getItemCreationAvailableData(self):
        """Check that we receive the list of available data for creating an item."""
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        setCorrectSettingsConfig(self.portal, minimal=True)

        availableData = set(ws4pmSettings._rest_getItemCreationAvailableData())
        self.assertEqual(availableData, {u'annexes',
                                         u'associatedGroups',
                                         u'category',
                                         u'copyGroups',
                                         u'decision',
                                         u'description',
                                         u'externalIdentifier',
                                         u'extraAttrs',
                                         u'groupsInCharge',
                                         u'ignore_validation_for',
                                         u'ignore_not_used_data',
                                         u'motivation',
                                         u'optionalAdvisers',
                                         u'preferredMeeting',
                                         u'proposingGroup',
                                         u'title',
                                         u'toDiscuss'})

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
        self.portal._volatile_cache_keys._p_changed = False  # Avoid ConflictError
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

    def test_rest_getDecidedMeetingDate(self):
        """Test the _rest_getDecidedMeetingDate method that should return
        the date of which the item has been actually decided."""
        setCorrectSettingsConfig(self.portal, minimal=True)
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')

        self.changeUser('admin')
        self._activate_wfas(('delayed', 'postpone_next_meeting', ))
        # Setting up sending to another meetingConfig
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'validated')},))
        cfg.setItemAutoSentToOtherMCStates((u'accepted', ))
        notify(ObjectEditedEvent(cfg))
        self.changeUser("pmManager")
        # Situation 1: item 'item_delayed' sent to PM will be delayed in a meeting 'meeting_delayed'
        # It will be replaced by 'item_decided' and decided in a next meeting 'meeting_decided'
        # It will also be sent to meetingConfig2
        meeting_delayed = self.create('Meeting', date=datetime(2024, 7, 20))
        item_delayed = self.create('MeetingItem', decision="A Decision", externalIdentifier=u'external1')
        item_delayed.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item_delayed.reindexObject(idxs=['sentToInfos', "externalIdentifier",])
        self.presentItem(item_delayed)
        self.decideMeeting(meeting_delayed)
        self.do(item_delayed, 'delay')
        item_decided = item_delayed.get_successor()
        meeting_decided_date = datetime(2024, 7, 21)
        meeting_decided = self.create('Meeting', date=meeting_decided_date)
        self.presentItem(item_decided)
        self.decideMeeting(meeting_decided)
        self.do(item_decided, 'accept')
        transaction.commit()
        self.assertEqual(
            ws4pmSettings._rest_getDecidedMeetingDate(
                {'externalIdentifier': 'external1', 'inTheNameOf': 'pmManager'},
                item_portal_type=cfg.getItemTypeName()
            ),
            meeting_decided_date
        )
        # Situation 2: 'item_decided' has been sent to meetingConfig2 as an other item 'item_sent'
        # and will be decided there too. We want the date of the meeting `meeting2_decided`
        # in which 'item_sent' is decided.
        item_sent = item_decided.get_successor()
        item_sent.category = 'deployment'  # categories are activated in cfg2
        self.setMeetingConfig(cfg2Id)
        meeting2_decided_date = datetime(2024, 7, 22)
        meeting2_decided = self.create('Meeting', date=meeting2_decided_date)
        self.presentItem(item_sent)
        self.decideMeeting(meeting2_decided)
        self.do(item_sent, 'accept')
        transaction.commit()
        self.assertEqual(
            ws4pmSettings._rest_getDecidedMeetingDate(
                {'externalIdentifier': 'external1', 'inTheNameOf': 'pmManager'},
                item_portal_type=cfg2.getItemTypeName()
            ),
            meeting2_decided_date
        )
        # It should still give us the meeting_decided_date for situation 1
        self.assertEqual(
            ws4pmSettings._rest_getDecidedMeetingDate(
                {'externalIdentifier': 'external1', 'inTheNameOf': 'pmManager'},
                item_portal_type=cfg.getItemTypeName()
            ),
            meeting_decided_date
        )

    def test_with_pm_session(self):
        """with_pm_session catches requests.RequestException and returns the configured empty_return."""
        setCorrectSettingsConfig(self.portal, minimal=True)
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        with patch('requests.Session.get', side_effect=requests_module.ConnectionError("connection timeout")):
            cleanMemoize(self.request)
            # default empty_return is None
            self.assertIsNone(ws4pmSettings._rest_checkIsLinked({'inTheNameOf': 'pmCreator1'}))
            # methods that declare empty_return=[] return that instead
            cleanMemoize(self.request)
            self.assertEqual(
                ws4pmSettings._rest_searchItems(
                    {'meetingConfigId': 'plonemeeting-assembly', 'inTheNameOf': 'pmCreator1'}
                ),
                []
            )

    def test_handle_rest_error(self):
        """_handle_rest_error always adds an error status message"""
        setCorrectSettingsConfig(self.portal, minimal=True)
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        # not on the settings panel: generic message without error detail
        with patch('requests.Session.get', side_effect=requests_module.ConnectionError("bad credentials")):
            cleanMemoize(self.request)
            ws4pmSettings._rest_checkIsLinked({'inTheNameOf': 'pmCreator1'})
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].type, 'error')
        self.assertEqual(messages[0].message, UNABLE_TO_CONNECT_ERROR)
        # on the settings panel: detailed message including the error text
        self.request.set('URL', self.portal.absolute_url() + '/@@ws4pmclient-settings')
        with patch('requests.Session.get', side_effect=requests_module.ConnectionError("bad credentials")):
            cleanMemoize(self.request)
            ws4pmSettings._rest_checkIsLinked({'inTheNameOf': 'pmCreator1'})
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].type, 'error')
        self.assertEqual(messages[0].message,
                         u'Unable to connect to PloneMeeting! The error message was : bad credentials!')

    def test_rest_checkConnection(self):
        """_rest_checkConnection probes PloneMeeting and surfaces errors via _handle_rest_error."""
        setCorrectSettingsConfig(self.portal, minimal=True)
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        self.request.set('URL', self.portal.absolute_url() + '/@@ws4pmclient-settings')
        # non-200 response raises and routes to _handle_rest_error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b''
        with patch('requests.Session.get', return_value=mock_response):
            cleanMemoize(self.request)
            ws4pmSettings._rest_checkConnection()
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].type, 'error')
        # 200 response: no error message
        mock_response.status_code = 200
        with patch('requests.Session.get', return_value=mock_response):
            cleanMemoize(self.request)
            ws4pmSettings._rest_checkConnection()
        self.assertEqual(len(IStatusMessage(self.request).show()), 0)


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    # add a prefix because we heritate from testMeeting and we do not want every tests of testMeeting to be run here...
    suite.addTest(makeSuite(testRESTMethods, prefix='test_'))
    return suite
