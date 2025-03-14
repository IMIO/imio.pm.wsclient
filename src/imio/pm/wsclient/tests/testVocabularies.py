# -*- coding: utf-8 -*-

from imio.pm.wsclient.browser import vocabularies
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase
from mock import patch
from natsort import humansorted
from plone import api
from WS4PMCLIENTTestCase import setCorrectSettingsConfig
from zope.component import getMultiAdapter


class testVocabularies(WS4PMCLIENTTestCase):
    """
    Test the vocabularies.
    """

    @patch("imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_getConfigInfos")
    def test_pm_meeting_config_id_vocabulary(self, _rest_getConfigInfos):
        """ """
        _rest_getConfigInfos.return_value = [
            {"id": u"plonegov-assembly", "title": u"PloneGov Assembly"},
            {"id": u"plonemeeting-assembly", "title": u"PloneMeeting Assembly"},
        ]
        raw_voc = vocabularies.pm_meeting_config_id_vocabularyFactory()
        self.assertEqual(len(raw_voc), 2)
        voc = [v for v in raw_voc]
        self.assertEqual(voc[0].value, "plonegov-assembly")
        self.assertEqual(voc[1].value, "plonemeeting-assembly")

    @patch("imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_getConfigInfos")
    @patch("imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_getMeetingsAcceptingItems")  # noqa
    def test_desired_meetingdates_vocabulary(self, _rest_getMeetingsAcceptingItems, _rest_getConfigInfos):
        """Ensure that vocabularies values are the expected"""
        _rest_getConfigInfos.return_value = [
            {"id": u"plonegov-assembly", "title": u"PloneGov Assembly"},
            {"id": u"plonemeeting-assembly", "title": u"PloneMeeting Assembly"},
        ]
        _rest_getMeetingsAcceptingItems.return_value = [
            {
                u"@extra_includes": [],
                u"@id": u"http://localhost:63033/plone/Members/pmManager/mymeetings/plonemeeting-assembly/o2",  # noqa
                u"@type": u"MeetingPma",
                u"UID": u"96b61ee6cc6d46b6a84c207d89e8ea51",
                u"created": u"2022-07-13T11:47:34+00:00",
                u"description": u"",
                u"enabled": None,
                u"id": u"o2",
                u"modified": u"2022-07-13T11:47:35+00:00",
                u"review_state": u"created",
                u"title": u"03 march 2013",
                u"date": u"2013-03-03T00:00:00",
            },
            {
                u"@extra_includes": [],
                u"@id": u"http://localhost:63033/plone/Members/pmManager/mymeetings/plonemeeting-assembly/o1",  # noqa
                u"@type": u"MeetingPma",
                u"UID": u"d7de4c8580bb404fbfbd5ea5963e9c64",
                u"created": u"2022-07-13T11:47:33+00:00",
                u"description": u"",
                u"enabled": None,
                u"id": u"o1",
                u"modified": u"2022-07-13T11:47:34+00:00",
                u"review_state": u"created",
                u"title": u"03 march 2013",
                u"date": u"2013-03-03T00:00:00",
            },
        ]

        raw_voc = vocabularies.desired_meetingdates_vocabularyFactory(api.portal.get())
        self.assertEqual(len(raw_voc), 2)

    @patch("imio.pm.wsclient.browser.settings.WS4PMClientSettings._rest_getConfigInfos")
    def test_categories_for_user_vocabulary(self, _rest_getConfigInfos):
        """Ensure that vocabularies values are the expected"""

        # Set the correct settings
        setCorrectSettingsConfig(self.portal, setConnectionParams=False, withValidation=False)
        ws4pmsettings = getMultiAdapter((self.portal, self.portal.REQUEST), name="ws4pmclient-settings")
        for i in range(len(ws4pmsettings.settings().field_mappings)):
            if ws4pmsettings.settings().field_mappings[i]["field_name"] == "category":
                del ws4pmsettings.settings().field_mappings[i]
                break
        self.portal.REQUEST.set("meetingConfigId", u"plonegov-assembly")

        # First test with categories
        _rest_getConfigInfos.return_value = [
            {
                "id": u"plonegov-assembly",
                "title": u"PloneGov Assembly",
                "categories": [
                    {
                        "id": "urbanisme",
                        "title": "Urbanisme",
                        "enabled": True,
                    },
                    {
                        "id": "finances",
                        "title": "Finances",
                        "enabled": True,
                    },
                ],
            },
            {"id": u"plonemeeting-assembly", "title": u"PloneMeeting Assembly"},
        ]
        voc = vocabularies.categories_for_user_vocabulary()(self.portal)
        self.assertListEqual(
            [(v.token, v.title) for v in voc], [("finances", u"Finances"), ("urbanisme", u"Urbanisme")]
        )

        # Second test without categories
        _rest_getConfigInfos.return_value = []
        voc = vocabularies.categories_for_user_vocabulary()(self.portal)
        self.assertListEqual(list(voc), [])
