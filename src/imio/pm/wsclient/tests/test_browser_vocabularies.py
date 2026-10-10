# -*- coding: utf-8 -*-
"""browser/vocabularies.py: values queried in PloneMeeting (F9)."""
from datetime import datetime
from imio.pm.wsclient.browser.vocabularies import (
    desired_meetingdates_vocabulary__call___cachekey,
)
from imio.pm.wsclient.config import CAN_NOT_CREATE_FOR_PROPOSING_GROUP_ERROR
from imio.pm.wsclient.config import CAN_NOT_CREATE_WITH_CATEGORY_ERROR
from imio.pm.wsclient.config import NO_CONFIG_INFOS_ERROR
from imio.pm.wsclient.config import NO_FIELD_MAPPINGS_ERROR
from imio.pm.wsclient.interfaces import IPreferredMeetings
from imio.pm.wsclient.testing import FAKE_PM
from imio.pm.wsclient.testing import WS4PMClientTestCase
from plone import api
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.interface import Interface
from zope.ramcache.interfaces.ram import IRAMCache
from zope.schema.interfaces import IVocabularyFactory

import unittest


class PreferredMeetings(object):
    """IPreferredMeetings of a consumer: the meetings of March only."""

    def __init__(self, context, meetings):
        self.meetings = meetings

    def get(self):
        return [meeting for meeting in self.meetings if meeting["date"].month == 3]


class VocabularyTestCase(WS4PMClientTestCase):

    name = None

    def vocabulary(self, context=None):
        return getUtility(IVocabularyFactory, self.name)(context or self.portal)

    def terms(self, context=None):
        return [(term.value, term.title) for term in self.vocabulary(context)]

    def not_connected(self):
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()


class TestPmMeetingConfigIdVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.pm_meeting_config_id_vocabulary"

    def test___call__(self):
        self.assertEqual(
            self.terms(),
            [
                (u"plonemeeting-assembly", u"PloneMeeting assembly"),
                (u"plonegov-assembly", u"PloneGov assembly"),
            ],
        )
        self.not_connected()
        self.assertEqual(self.terms(), [])


class TestPossiblePermissionsVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.possible_permissions_vocabulary"

    def test___call__(self):
        values = [value for value, title in self.terms()]
        self.assertIn("View", values)
        self.assertIn("Modify portal content", values)


class TestPmItemDataVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.pm_item_data_vocabulary"

    def test___call__(self):
        values = [value for value, title in self.terms()]
        self.assertEqual(values[:3], [u"annexes", u"associatedGroups", u"category"])
        self.assertIn(u"copyGroups", values)
        self.not_connected()
        self.assertEqual(self.terms(), [])


class TestProposingGroupsForUserVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.proposing_groups_for_user_vocabulary"

    def test___call__(self):
        developers, vendors = FAKE_PM.orgs
        self.assertEqual(self.terms(), [(developers["UID"], u"Developers")])
        # the creators groups of the user, sorted by title
        FAKE_PM.users[u"pmCreator1"]["groups"].append(u"vendors_creators")
        self.clean_memoize()
        self.assertEqual(
            self.terms(),
            [(developers["UID"], u"Developers"), (vendors["UID"], u"Vendors")],
        )
        # a proposing group forced by the field mappings
        field_mappings = self.settings.field_mappings
        self.settings.field_mappings = field_mappings + [
            {"field_name": u"proposingGroup", "expression": u"string:vendors"}
        ]
        self.assertEqual(self.terms(), [(vendors["UID"], u"Vendors")])
        self.assertFalse(self.request.get("error_in_vocabularies"))
        FAKE_PM.users[u"pmCreator1"]["groups"] = [u"developers_creators"]
        self.clean_memoize()
        self.assertEqual(self.terms(), [])
        self.assertTrue(self.request.get("error_in_vocabularies"))
        self.assertEqual(self.messages(), [CAN_NOT_CREATE_FOR_PROPOSING_GROUP_ERROR])
        # a wrong expression
        self.settings.field_mappings = field_mappings + [
            {"field_name": u"proposingGroup", "expression": u"python: object.unknown()"}
        ]
        self.assertEqual(self.terms(), [])
        self.assertTrue(
            self.messages()[0].startswith(
                u"There was an error evaluating the TAL expression 'python: object.unknown()' for the field "
                u"'proposingGroup'! The error was : "
            )
        )
        # no field mappings
        self.settings.field_mappings = []
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [NO_FIELD_MAPPINGS_ERROR])
        # the user is unknown in PloneMeeting: no message (shown by the form)
        self.settings.field_mappings = field_mappings
        del FAKE_PM.users[u"pmCreator1"]
        self.clean_memoize()
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [])
        # PloneMeeting can not be reached: no message
        self.not_connected()
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [])


class TestCategoriesForUserVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.categories_for_user_vocabulary"

    def test___call__(self):
        # the category forced by the field mappings of the layer
        self.request.set("meetingConfigId", "plonegov-assembly")
        self.assertEqual(self.terms(), [(u"deployment", u"Deployment topics")])
        # the categories of the config, sorted by title
        field_mappings = self.settings.field_mappings
        self.settings.field_mappings = [
            mapping for mapping in field_mappings if mapping["field_name"] != "category"
        ]
        self.assertEqual(
            [value for value, title in self.terms()],
            [
                u"deployment",
                u"development",
                u"events",
                u"maintenance",
                u"projects",
                u"research",
            ],
        )
        # the config of the submitted form
        self.request.set("meetingConfigId", "")
        self.request.form["form.widgets.meetingConfigId"] = u"plonegov-assembly"
        self.assertEqual(len(self.terms()), 6)
        # no categories in plonemeeting-assembly
        self.request.set("meetingConfigId", "plonemeeting-assembly")
        self.assertEqual(self.terms(), [])
        self.assertFalse(self.request.get("error_in_vocabularies"))
        # a forced category that does not exist
        self.request.set("meetingConfigId", "plonegov-assembly")
        self.settings.field_mappings = [
            {"field_name": u"category", "expression": u"string:unknown"}
        ]
        self.assertEqual(self.terms(), [])
        self.assertTrue(self.request.get("error_in_vocabularies"))
        self.assertEqual(self.messages(), [CAN_NOT_CREATE_WITH_CATEGORY_ERROR])
        # a wrong expression
        self.settings.field_mappings = [
            {"field_name": u"category", "expression": u"python: object.unknown()"}
        ]
        self.assertEqual(self.terms(), [])
        self.assertTrue(
            self.messages()[0].startswith(
                u"There was an error evaluating the TAL expression 'python: object.unknown()' for the field 'category'!"
            )
        )
        # no field mappings
        self.settings.field_mappings = []
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [NO_FIELD_MAPPINGS_ERROR])
        # no configs
        self.settings.field_mappings = field_mappings
        FAKE_PM.configs = []
        self.clean_memoize()
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [NO_CONFIG_INFOS_ERROR])
        # PloneMeeting can not be reached: no message
        self.not_connected()
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [])


class TestDesiredMeetingdatesVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.possible_meetingdates_vocabulary"

    def test___call__(self):
        meeting_1 = FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2013, 3, 3))
        FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2013, 3, 3, 14, 30))
        meeting_3 = FAKE_PM.add_meeting(u"plonegov-assembly", datetime(2013, 8, 3))
        self.request.set("meetingConfigId", "plonemeeting-assembly")
        self.assertEqual(
            self.terms(),
            [
                (meeting_1["UID"], u"03/03/2013 00:00"),
                (FAKE_PM.meetings[1]["UID"], u"03/03/2013 14:30"),
            ],
        )
        # cached for the config
        FAKE_PM.meetings.remove(meeting_1)
        self.assertEqual(len(self.terms()), 2)
        self.request.set("meetingConfigId", "plonegov-assembly")
        vocabulary = self.vocabulary()
        self.assertEqual(
            [(term.value, term.token, term.title) for term in vocabulary],
            [(meeting_3["UID"], meeting_3["UID"], u"03/08/2013 00:00")],
        )
        # the meetings preferred by the consumer
        getUtility(IRAMCache).invalidateAll()
        FAKE_PM.add_meeting(u"plonegov-assembly", datetime(2013, 3, 3))
        gsm = getGlobalSiteManager()
        gsm.registerAdapter(
            PreferredMeetings, (Interface, Interface), IPreferredMeetings
        )
        try:
            self.assertEqual(
                [title for value, title in self.terms()], [u"03/03/2013 00:00"]
            )
        finally:
            gsm.unregisterAdapter(
                PreferredMeetings, (Interface, Interface), IPreferredMeetings
            )
        # no meetings
        getUtility(IRAMCache).invalidateAll()
        del FAKE_PM.meetings[:]
        self.assertEqual(self.terms(), [])
        # no configs
        getUtility(IRAMCache).invalidateAll()
        FAKE_PM.configs = []
        self.clean_memoize()
        self.assertEqual(self.terms(), [])
        self.assertEqual(self.messages(), [NO_CONFIG_INFOS_ERROR])

    @unittest.expectedFailure
    def test___call___not_connected(self):
        """Master bug: an empty vocabulary is cached when PloneMeeting can not be reached
        (and the meetings of the first user/element for everybody)."""
        FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2013, 3, 3))
        self.request.set("meetingConfigId", "plonemeeting-assembly")
        self.not_connected()
        self.assertEqual(self.terms(), [])
        self.settings.pm_password = u"Meeting_12"
        self.clean_memoize()
        self.assertEqual(len(self.terms()), 1)


class TestAnnexesForUserVocabulary(VocabularyTestCase):

    name = u"imio.pm.wsclient.annexes_for_user_vocabulary"

    def test___call__(self):
        # the files of a folder (ISendableAnnexesToPM of testing.zcml)
        folder = api.content.create(container=self.portal, type="Folder", title=u"Mail")
        annex = self.create_file(folder, title=u"Annex")
        self.create_document(folder)
        self.assertEqual(self.terms(folder), [(annex.UID(), "Annex")])
        # no ISendableAnnexesToPM
        self.assertEqual(self.terms(self.create_document()), [])


class TestVocabularies(WS4PMClientTestCase):
    def test_desired_meetingdates_vocabulary__call___cachekey(self):
        self.request.set("meetingConfigId", "plonegov-assembly")
        self.assertEqual(
            desired_meetingdates_vocabulary__call___cachekey(None, None, None),
            "plonegov-assembly",
        )
        self.request.set("meetingConfigId", "")
        self.assertEqual(
            desired_meetingdates_vocabulary__call___cachekey(None, None, None), ""
        )
