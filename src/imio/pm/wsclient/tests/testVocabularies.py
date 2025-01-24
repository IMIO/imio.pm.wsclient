# -*- coding: utf-8 -*-

from imio.pm.wsclient.browser import vocabularies
from imio.pm.wsclient.tests.WS4PMCLIENTTestCase import WS4PMCLIENTTestCase
from plone import api

from mock import patch


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
    def test_desired_meetingdates_vocabulary(
        self, _rest_getMeetingsAcceptingItems, _rest_getConfigInfos
    ):
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
        _rest_getConfigInfos.return_value = [
            {"id": u"plonegov-assembly", "title": u"PloneGov Assembly"},
            {"id": u"plonemeeting-assembly", "title": u"PloneMeeting Assembly"},
            {"id": u"meeting-config-college", "title": u'Coll\xe8ge'},
        ]

        import ipdb; ipdb.set_trace()
        registry_key = "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.field_mappings"
        # [u'annexes', u'associatedGroups', u'budgetInfos', u'category', u'classifier', u'committeeObservations', u'committeeTranscript', u'copyGroups', u'decision', u'decisionEnd', u'decisionSuite', u'description', u'detailedDescription', u'emergency', u'emergencyMotivation', u'externalIdentifier', u'extraAttrs', u'groupsInCharge', u'ignore_validation_for', u'inAndOutMoves', u'internalNotes', u'itemInitiator', u'itemKeywords', u'manuallyLinkedItems', u'marginalNotes', u'meetingDeadlineDate', u'meetingManagersNotes', u'motivation', u'notes', u'observations', u'optionalAdvisers', u'oralQuestion', u'otherMeetingConfigsClonableToEmergency', u'otherMeetingConfigsClonableToFieldDecision', u'otherMeetingConfigsClonableToFieldDecisionEnd', u'otherMeetingConfigsClonableToFieldDecisionSuite', u'otherMeetingConfigsClonableToPrivacy', u'pollType', u'pollTypeObservations', u'preferredMeeting', u'privacy', u'proposingGroup', u'sendToAuthority', u'takenOverBy', u'textCheckList', u'title', u'toDiscuss', u'votesObservations', u'votesResult', u'votesResult_after_motivation']
        field_mappings = [
            {'expression': u'context/title', 'field_name': u'title'},
            {'expression': u"python: u'{}\\n{}'.format(context.description, context.restrictedTraverse('@@IncomingmailWSClient').detailed_description())", 'field_name': u'description'},
            {'expression': u'context/@@IncomingmailWSClient/get_main_files', 'field_name': u'annexes'}
        ]
        # FIXME *** WrongContainedType: ([ConstraintNotSatisfied(u'title'), ConstraintNotSatisfied(u'description'), ConstraintNotSatisfied(u'annexes')], 'value')
        api.portal.set_registry_record(registry_key, field_mappings)

        raw_voc = vocabularies.categories_for_user_vocabularyFactory(api.portal.get())
        self.assertEqual(len(raw_voc), 1)
        self.assertEqual(raw_voc[0].value, "meeting-config-college")
        self.assertEqual(raw_voc[0].title, u'Coll\xe8ge')
