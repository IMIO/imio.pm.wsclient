# -*- coding: utf-8 -*-
"""browser/settings.py: control panel, REST client (F2, F3, F4)."""
from AccessControl import Unauthorized
from datetime import datetime
from imio.pm.wsclient.browser.settings import IWS4PMClientSettings
from imio.pm.wsclient.browser.settings import notify_configuration_changed
from imio.pm.wsclient.browser.settings import WS4PMClientSettingsEditForm
from imio.pm.wsclient.config import ACTION_SUFFIX
from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from imio.pm.wsclient.testing import FAKE_PM
from imio.pm.wsclient.testing import PM_URL
from imio.pm.wsclient.testing import USER_PASSWORD
from imio.pm.wsclient.testing import WS4PMClientTestCase
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.registry.events import RecordModifiedEvent
from plone.registry.interfaces import IRegistry
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.tales.tales import CompilerError

import six
import unittest


class TestWS4PMClientSettingsEditForm(WS4PMClientTestCase):

    def edit_form(self, **form):
        self.request.form.update(form)
        self.request.set("URL", self.portal.absolute_url() + "/@@ws4pmclient-settings")
        edit_form = WS4PMClientSettingsEditForm(self.portal, self.request)
        edit_form.update()
        return edit_form

    def test_updateFields(self):
        # connected: every field can be edited
        edit_form = self.edit_form()
        self.assertEqual(edit_form.widgets["generated_actions"].mode, "input")
        self.assertEqual(edit_form.widgets["field_mappings"].mode, "input")
        self.assertEqual(self.messages(), [])
        # an URL entered in the form is used instead of the saved one: PloneMeeting
        # can not be reached, the error is shown and the generated actions and
        # field mappings are only displayed
        self.clean_memoize()
        edit_form = self.edit_form(**{"form.widgets.pm_url": u"http://wrong.example.org"})
        self.assertEqual(edit_form.widgets["generated_actions"].mode, "display")
        self.assertEqual(edit_form.widgets["field_mappings"].mode, "display")
        # and back to edition once connected
        self.clean_memoize()
        del self.request.form["form.widgets.pm_url"]
        self.assertEqual(self.edit_form().widgets["generated_actions"].mode, "input")
        self.assertEqual(self.messages(), [
            u"Unable to connect to PloneMeeting! The error message was : "
            u"Failed to establish a new connection to http://wrong.example.org/@infos!"])

    @unittest.expectedFailure
    def test_updateFields_wrong_password_message(self):
        """Master bug: the error answered by PloneMeeting is lost: KeyError, plone.restapi
        errors have no 'error' key."""
        self.edit_form(**{"form.widgets.pm_password": u"wrongPassword"})
        self.assertEqual(self.messages(), [
            u"Unable to connect to PloneMeeting! The error message was : Wrong login and/or password.!"])

    def test_handleSave(self):
        # not connected: the generated actions and field mappings are kept
        generated_actions = self.settings.generated_actions
        self.edit_form(**{
            "form.widgets.pm_url": u"http://wrong.example.org",
            "form.widgets.pm_timeout": u"20",
            "form.widgets.pm_username": u"pmManager",
            "form.widgets.pm_password": u"Meeting_12",
            "form.widgets.only_one_sending": [u"selected"],
            "form.widgets.only_one_sending-empty-marker": u"1",
            "form.buttons.save": u"Save",
        })
        self.assertEqual(self.settings.pm_url, u"http://wrong.example.org")
        self.assertEqual(self.settings.pm_timeout, 20)
        self.assertEqual(self.settings.generated_actions, generated_actions)
        self.assertIn(u"Changes saved", self.messages())
        self.assertEqual(self.request.response.getHeader("location"), "@@ws4pmclient-settings")

    def test_handleCancel(self):
        edit_form = self.edit_form(**{"form.widgets.pm_timeout": u"20", "form.buttons.cancel": u"Cancel"})
        self.assertEqual(self.settings.pm_timeout, 10)
        self.assertEqual(self.messages(), [u"Edit cancelled"])
        self.assertEqual(self.request.response.getHeader("location"),
                         "{0}/{1}".format(self.portal.absolute_url(), edit_form.control_panel_view))


class TestWS4PMClientSettings(WS4PMClientTestCase):

    def test_settings(self):
        # only for users having "Manage portal"
        logout()
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, "@@ws4pmclient-settings")
        login(self.portal, "pmCreator1")
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, "@@ws4pmclient-settings")
        login(self.portal, TEST_USER_NAME)
        settings = self.portal.restrictedTraverse("@@ws4pmclient-settings").settings()
        self.assertEqual(sorted(settings.__schema__.names()), [
            "allowed_annexes_types", "field_mappings", "generated_actions", "only_one_sending", "pm_password",
            "pm_timeout", "pm_url", "pm_username", "select_all_attachments_by_default", "user_mappings",
            "viewlet_display_condition"])
        self.assertEqual(settings.pm_url, PM_URL)

    def test_url(self):
        self.assertEqual(self.ws4pmSettings.url, PM_URL)
        # the value entered in the control panel form
        self.request.form["form.widgets.pm_url"] = u"http://other.example.org"
        self.assertEqual(self.ws4pmSettings.url, u"http://other.example.org")
        del self.request.form["form.widgets.pm_url"]
        self.settings.pm_url = None
        self.assertEqual(self.ws4pmSettings.url, "")

    def test_username(self):
        self.assertEqual(self.ws4pmSettings.username, u"pmManager")
        self.request.form["form.widgets.pm_username"] = u"pmCreator1"
        self.assertEqual(self.ws4pmSettings.username, u"pmCreator1")
        del self.request.form["form.widgets.pm_username"]
        self.settings.pm_username = None
        self.assertEqual(self.ws4pmSettings.username, "")

    def test__rest_connectToPloneMeeting(self):
        session = self.ws4pmSettings._rest_connectToPloneMeeting()
        self.assertEqual(session.auth, (u"pmManager", u"Meeting_12"))
        self.assertEqual(session.headers, {"Accept": "application/json", "Content-Type": "application/json"})
        # with an invalid url, it fails
        self.settings.pm_url = PM_URL + u"invalidEndOfURL"
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings._rest_connectToPloneMeeting())
        # with a wrong password, it fails
        self.settings.pm_url = PM_URL
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings._rest_connectToPloneMeeting())
        # the error is only shown in the control panel
        self.assertEqual(self.messages(), [])

    def test__format_rest_query_url(self):
        self.assertEqual(self.ws4pmSettings._format_rest_query_url("@search"), PM_URL + "/@search")
        url = self.ws4pmSettings._format_rest_query_url(
            "@get", uid="1234", extra_include="meeting,annexes", in_name_of=None, fullobjects=None)
        # comma separated values are repeated, empty values ignored, except fullobjects
        self.assertTrue(url.startswith(PM_URL + "/@get?"))
        self.assertEqual(sorted(url.split("?")[1].split("&")),
                         ["extra_include=annexes", "extra_include=meeting", "fullobjects", "uid=1234"])

    def test__rest_checkIsLinked(self):
        item1 = FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmCreator1", title=u"Item 1",
                                 externalIdentifier=u"external1")
        result = self.ws4pmSettings._rest_checkIsLinked({"UID": item1["UID"], "externalIdentifier": u"external1"})
        self.assertEqual(result["UID"], item1["UID"])
        self.assertEqual(result["extra_include_linked_items_items_total"], 0)
        # item2 was delayed: it is linked to its successor
        item2 = FAKE_PM.add_item(u"plonemeeting-assembly", u"vendors", u"pmCreator2", title=u"Item 2",
                                 externalIdentifier=u"external2")
        item2_link = FAKE_PM.add_item(u"plonemeeting-assembly", u"vendors", u"pmCreator2", title=u"Item 2")
        item2.update(review_state=u"delayed", successors=[item2_link["UID"]])
        result = self.ws4pmSettings._rest_checkIsLinked({"UID": item2["UID"], "externalIdentifier": u"external2"})
        self.assertEqual(result["UID"], item2["UID"])
        self.assertEqual(result["extra_include_linked_items_items_total"], 1)
        self.assertEqual(result["extra_include_linked_items"][0]["UID"], item2_link["UID"])
        # no linked item
        self.assertFalse(self.ws4pmSettings._rest_checkIsLinked(
            {"externalIdentifier": u"external3", "config_id": u"plonemeeting-assembly"}))
        # not connected
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings._rest_checkIsLinked({"externalIdentifier": u"external1"}))

    def test__rest_getConfigInfos(self):
        configInfos = self.ws4pmSettings._rest_getConfigInfos()
        self.assertEqual([info["id"] for info in configInfos], [u"plonemeeting-assembly", u"plonegov-assembly"])
        self.assertEqual(configInfos[1]["title"], u"PloneGov assembly")
        # by default, no categories, asked with showCategories
        self.assertNotIn("categories", configInfos[1])
        configInfos = self.ws4pmSettings._rest_getConfigInfos(showCategories=True)
        self.assertEqual(configInfos[0]["categories"], [])
        self.assertEqual(len(configInfos[1]["categories"]), 6)
        self.assertEqual(configInfos[1]["categories"][0]["id"], u"deployment")
        # not connected
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings._rest_getConfigInfos())

    def test__rest_getUserInfos(self):
        login(self.portal, "pmCreator1")
        # groups of the user for a suffix
        user_infos = self.ws4pmSettings._rest_getUserInfos(showGroups=True, suffix="creators")
        self.assertEqual(user_infos["id"], u"pmCreator1")
        self.assertEqual(user_infos["extra_include_groups_items_total"], 1)
        self.assertEqual(user_infos["extra_include_groups"][0]["id"], u"developers")
        # a suffix that does not match any group
        user_infos = self.ws4pmSettings._rest_getUserInfos(showGroups=True, suffix="observers")
        self.assertEqual(user_infos["id"], u"pmCreator1")
        self.assertEqual(user_infos["extra_include_groups_items_total"], 0)
        # every group
        user_infos = self.ws4pmSettings._rest_getUserInfos(showGroups=True)
        self.assertEqual(user_infos["extra_include_groups_items_total"], 1)
        self.assertEqual(user_infos["extra_include_groups"][0]["id"], u"developers")
        # no groups by default
        user_infos = self.ws4pmSettings._rest_getUserInfos()
        self.assertEqual(user_infos["id"], u"pmCreator1")
        self.assertNotIn("extra_include_groups", user_infos)
        # a user unknown in PloneMeeting
        del FAKE_PM.users[u"pmCreator1"]
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings._rest_getUserInfos())

    def test__rest_searchItems(self):
        # items are only visible to the users of their proposing group
        item1 = FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmCreator1", title=u"Same title")
        item2 = FAKE_PM.add_item(u"plonemeeting-assembly", u"vendors", u"pmCreator2", title=u"Same title")
        login(self.portal, "pmCreator1")
        result = self.ws4pmSettings._rest_searchItems({"Title": u"Same title"})
        self.assertEqual([item["UID"] for item in result], [item1["UID"]])
        login(self.portal, "pmCreator2")
        result = self.ws4pmSettings._rest_searchItems({"Title": u"Same title"})
        self.assertEqual([item["UID"] for item in result], [item2["UID"]])
        # an error answered by PloneMeeting: no item
        login(self.portal, TEST_USER_NAME)
        self.settings.user_mappings = []
        self.assertEqual(self.ws4pmSettings._rest_searchItems({"Title": u"Same title"}), [])

    def test__rest_getItemInfos(self):
        item = FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmManager", title=u"Item")
        # the user of the settings sees everything
        self.settings.user_mappings = [{"local_userid": six.text_type(TEST_USER_ID), "pm_userid": u"pmManager"}]
        self.assertEqual(len(self.ws4pmSettings._rest_getItemInfos({"UID": item["UID"]})), 1)
        # inTheNameOf the connected user
        login(self.portal, "pmCreator1")
        infos = self.ws4pmSettings._rest_getItemInfos({"UID": item["UID"], "extra_include": "config"})
        self.assertEqual(infos[0]["UID"], item["UID"])
        self.assertEqual(infos[0]["extra_include_config"]["id"], u"plonemeeting-assembly")
        login(self.portal, "pmCreator2")
        self.assertEqual(self.ws4pmSettings._rest_getItemInfos({"UID": item["UID"]}), [])

    def test__rest_getAnnex(self):
        FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmCreator1", title=u"Item", annexes=[
            {"@type": "annex", "title": u"Annex", "file": {"filename": u"annex.txt", "data": u"aGVsbG8K"}}])
        url = PM_URL + u"/Members/pmCreator1/mymeetings/plonemeeting-assembly/item/annex.txt/@@download/file"
        self.assertEqual(self.ws4pmSettings._rest_getAnnex(url), b"hello\n")
        self.assertEqual(self.ws4pmSettings._rest_getAnnex(url + u"-unknown"), "")
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertEqual(self.ws4pmSettings._rest_getAnnex(url), "")

    def test__rest_getMeetingsAcceptingItems(self):
        """Meetings in the state 'created' and 'frozen', and 'decided' for a MeetingManager."""
        data = {"meetingConfigId": u"plonemeeting-assembly", "inTheNameOf": u"pmCreator1"}
        self.assertEqual(self.ws4pmSettings._rest_getMeetingsAcceptingItems(dict(data)), [])
        meeting_1 = FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2013, 3, 3))
        meeting_2 = FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2013, 3, 3))
        FAKE_PM.add_meeting(u"plonegov-assembly", datetime(2013, 3, 3))
        self.assertEqual(len(self.ws4pmSettings._rest_getMeetingsAcceptingItems(dict(data))), 2)
        meeting_2["review_state"] = u"frozen"
        self.assertEqual(len(self.ws4pmSettings._rest_getMeetingsAcceptingItems(dict(data))), 2)
        meeting_2["review_state"] = u"decided"
        meetings = self.ws4pmSettings._rest_getMeetingsAcceptingItems(dict(data))
        self.assertEqual([meeting["UID"] for meeting in meetings], [meeting_1["UID"]])
        # without inTheNameOf, the user mapped to the connected user
        meetings = self.ws4pmSettings._rest_getMeetingsAcceptingItems({"meetingConfigId": u"plonemeeting-assembly"})
        self.assertEqual([meeting["UID"] for meeting in meetings], [meeting_1["UID"]])
        # a MeetingManager gets every meeting
        meetings = self.ws4pmSettings._rest_getMeetingsAcceptingItems(
            {"meetingConfigId": u"plonemeeting-assembly", "inTheNameOf": u"pmManager"})
        self.assertEqual(len(meetings), 2)
        self.assertEqual(meetings[0]["date"], u"2013-03-03T00:00:00")

    def test__rest_getDecidedMeetingDate(self):
        """The date of the meeting deciding the item, following delayed and sent items."""
        # the item sent to PloneMeeting is delayed, its successor is decided in a next meeting
        # and sent to plonegov-assembly where it is decided too
        meeting_delayed = FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2024, 7, 20), u"decided")
        meeting_decided = FAKE_PM.add_meeting(u"plonemeeting-assembly", datetime(2024, 7, 21), u"decided")
        meeting2_decided = FAKE_PM.add_meeting(u"plonegov-assembly", datetime(2024, 7, 22), u"decided")
        item_delayed = FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmManager", title=u"Item",
                                        externalIdentifier=u"external1")
        item_decided = FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmManager", title=u"Item")
        item_sent = FAKE_PM.add_item(u"plonegov-assembly", u"developers", u"pmManager", title=u"Item",
                                     category=u"deployment")
        item_delayed.update(review_state=u"delayed", meeting=meeting_delayed["UID"], successors=[item_decided["UID"]])
        item_decided.update(review_state=u"accepted", meeting=meeting_decided["UID"], successors=[item_sent["UID"]])
        item_sent.update(review_state=u"accepted", meeting=meeting2_decided["UID"])
        data = {"externalIdentifier": u"external1", "inTheNameOf": u"pmManager"}
        self.assertEqual(self.ws4pmSettings._rest_getDecidedMeetingDate(dict(data), u"MeetingItemPma"),
                         datetime(2024, 7, 21))
        self.assertEqual(self.ws4pmSettings._rest_getDecidedMeetingDate(dict(data), u"MeetingItemPga"),
                         datetime(2024, 7, 22))
        # the item sent to PloneMeeting is decided
        item_delayed.update(review_state=u"accepted")
        self.assertEqual(self.ws4pmSettings._rest_getDecidedMeetingDate(dict(data), u"MeetingItemPma"),
                         datetime(2024, 7, 20))
        # not decided, not found
        item_sent["review_state"] = u"itemcreated"
        self.assertIsNone(self.ws4pmSettings._rest_getDecidedMeetingDate(dict(data), u"MeetingItemPga"))
        self.assertIsNone(self.ws4pmSettings._rest_getDecidedMeetingDate(
            {"externalIdentifier": u"unknown", "inTheNameOf": u"pmManager"}, u"MeetingItemPma"))

    def test__rest_getItemTemplate(self):
        item = FAKE_PM.add_item(u"plonemeeting-assembly", u"developers", u"pmManager", title=u"Item")
        data = {"itemUID": item["UID"], "templateId": u"itemTemplate__format__odt"}
        self.settings.user_mappings = [{"local_userid": six.text_type(TEST_USER_ID), "pm_userid": u"pmManager"}]
        self.assertEqual(self.ws4pmSettings._rest_getItemTemplate(dict(data)).content, b"Meeting item (odt)")
        # inTheNameOf the connected user
        login(self.portal, "pmCreator1")
        self.assertEqual(self.ws4pmSettings._rest_getItemTemplate(dict(data)).content, b"Meeting item (odt)")
        # pmCreator2 can not see the item
        login(self.portal, "pmCreator2")
        self.assertIsNone(self.ws4pmSettings._rest_getItemTemplate(dict(data)))
        self.assertEqual(self.messages(), [
            u"An error occured while generating the document in PloneMeeting! "
            u"The error message was : 'extra_include_pod_templates'"])
        login(self.portal, "pmCreator1")
        for template_id, error in (
                (u"", u"Server raised fault: 'You can not access this template!'"),
                (u"unknown__format__odt", u"Unkown template id 'unknown'"),
                (u"itemTemplate__format__doc", u"Unknown output format 'doc' for template id 'itemTemplate'")):
            self.assertIsNone(self.ws4pmSettings._rest_getItemTemplate(
                {"itemUID": item["UID"], "templateId": template_id}))
            self.assertEqual(self.messages(), [
                u"An error occured while generating the document in PloneMeeting! The error message was : " + error])

    def test__rest_getItemCreationAvailableData(self):
        self.assertEqual(set(self.ws4pmSettings._rest_getItemCreationAvailableData()), {
            u"annexes", u"associatedGroups", u"category", u"copyGroups", u"decision", u"description",
            u"externalIdentifier", u"extraAttrs", u"groupsInCharge", u"ignore_validation_for",
            u"ignore_not_used_data", u"motivation", u"optionalAdvisers", u"preferredMeeting", u"proposingGroup",
            u"title", u"toDiscuss"})

    def test__rest_createItem(self):
        """The item is created inTheNameOf the user mapped to the connected user."""
        meeting = FAKE_PM.add_meeting(u"plonegov-assembly", datetime(2013, 3, 3), u"frozen")
        data = {u"title": u"My sample item",
                u"category": u"deployment",
                u"description": u"<p>My description</p>",
                u"decision": u"<p>My d\xe9cision</p>",
                u"preferredMeeting": meeting["UID"],
                u"externalIdentifier": u"my-external-identifier",
                u"extraAttrs": [{"key": "internalNotes", "value": "<p>Internal notes</p>"}]}
        uid, warnings = self.ws4pmSettings._rest_createItem(u"plonegov-assembly", u"developers", dict(data))
        self.assertEqual(warnings, [])
        item = FAKE_PM.items[-1]
        self.assertEqual(item["UID"], uid)
        self.assertEqual(item["creator"], u"pmCreator1")
        self.assertEqual(item["proposingGroup"], u"developers")
        for key in (u"title", u"category", u"description", u"decision", u"preferredMeeting",
                    u"externalIdentifier"):
            self.assertEqual(item[key], data[key])
        self.assertEqual(item["internalNotes"], u"<p>Internal notes</p>")
        # PloneMeeting refuses the item: the error is shown
        data[u"category"] = u"unexisting-category-id"
        self.assertIsNone(self.ws4pmSettings._rest_createItem(u"plonegov-assembly", u"developers", dict(data)))
        self.assertEqual(self.messages(), [
            u"An error occured during the item creation in PloneMeeting! The error message was : "
            u"[{'field': 'category', 'message': u'Please select a category.', 'error': 'ValidationError'}]"])
        # the validation of some fields can be ignored
        del data[u"category"]
        data[u"ignore_validation_for"] = u"category"
        uid, warnings = self.ws4pmSettings._rest_createItem(u"plonegov-assembly", u"developers", dict(data))
        self.assertEqual(FAKE_PM.items[-1]["UID"], uid)
        self.assertNotIn("category", FAKE_PM.items[-1])
        # a proposing group of another user
        self.assertIsNone(self.ws4pmSettings._rest_createItem(u"plonegov-assembly", u"vendors", dict(data)))
        self.assertEqual(self.messages(), [
            u"An error occured during the item creation in PloneMeeting! The error message was : "
            u"[{'field': 'proposingGroup', 'message': u'Proposing group is not available for user.', "
            u"'error': 'ValidationError'}]"])
        # not connected
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings._rest_createItem(u"plonegov-assembly", u"developers", dict(data)))

    @unittest.expectedFailure
    def test__rest_createItem_warnings(self):
        """Master bug: the warnings of PloneMeeting are in '@warnings', the client reads 'warnings'."""
        data = {u"title": u"My sample item", u"ignore_validation_for": u"category"}
        uid, warnings = self.ws4pmSettings._rest_createItem(u"plonegov-assembly", u"developers", data)
        self.assertEqual(warnings, [u"Validation was ignored for following fields: category."])

    def test__getUserIdToUseInTheNameOfWith(self):
        # no user_mappings: the connected user
        self.settings.user_mappings = []
        self.assertEqual(self.ws4pmSettings._getUserIdToUseInTheNameOfWith(), TEST_USER_ID)
        # the connected user is the user of the settings
        self.settings.pm_username = six.text_type(TEST_USER_ID)
        self.assertIsNone(self.ws4pmSettings._getUserIdToUseInTheNameOfWith())
        self.assertEqual(self.ws4pmSettings._getUserIdToUseInTheNameOfWith(mandatory=True), TEST_USER_ID)
        # a user mapping to another user
        api.user.create(username="lambda", email="lambda@example.org", password=USER_PASSWORD)
        self.settings.user_mappings = [
            {"local_userid": u"localUserId", "pm_userid": u"pmCreator1"},
            {"local_userid": u"lambda", "pm_userid": u"aUserInPloneMeeting"}]
        login(self.portal, "lambda")
        self.assertEqual(self.ws4pmSettings._getUserIdToUseInTheNameOfWith(), u"aUserInPloneMeeting")
        # a user mapping to the user of the settings
        self.settings.user_mappings = [{"local_userid": u"lambda", "pm_userid": six.text_type(TEST_USER_ID)}]
        self.assertIsNone(self.ws4pmSettings._getUserIdToUseInTheNameOfWith())
        self.assertEqual(self.ws4pmSettings._getUserIdToUseInTheNameOfWith(mandatory=True), TEST_USER_ID)
        # no mapping for this user: his own id
        self.settings.user_mappings = [{"local_userid": u"otherUser", "pm_userid": u"otherUserInPloneMeeting"}]
        self.assertEqual(self.ws4pmSettings._getUserIdToUseInTheNameOfWith(), "lambda")

    def test_checkAlreadySentToPloneMeeting(self):
        """True if linked to an item of the configs, annotations of deleted items are wiped out."""
        document = self.create_document()
        annotations = IAnnotations(document)
        # not sent: no call to PloneMeeting
        self.assertFalse(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document, (u"plonemeeting-assembly",)))
        self.assertNotIn(WS4PMCLIENT_ANNOTATION_KEY, annotations)
        item1 = self.send_to_pm(document)
        self.assertEqual(annotations[WS4PMCLIENT_ANNOTATION_KEY], [u"plonemeeting-assembly"])
        self.assertTrue(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document, (u"plonemeeting-assembly",)))
        self.assertFalse(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document, (u"plonegov-assembly",)))
        # the item was deleted in PloneMeeting: the annotation is wiped out
        FAKE_PM.items.remove(item1)
        self.assertFalse(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document, (u"plonemeeting-assembly",)))
        self.assertNotIn(WS4PMCLIENT_ANNOTATION_KEY, annotations)
        # sent again and to another config
        self.send_to_pm(document)
        self.send_to_pm(document, "plonegov-assembly", **{"form.widgets.category": [u"deployment"]})
        self.assertEqual(annotations[WS4PMCLIENT_ANNOTATION_KEY], [u"plonemeeting-assembly", u"plonegov-assembly"])
        self.assertTrue(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document, (u"plonegov-assembly",)))
        # PloneMeeting can not be reached
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertIsNone(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document))
        # without configs, every config of the annotation is checked
        self.settings.pm_password = u"Meeting_12"
        self.clean_memoize()
        del FAKE_PM.items[:]
        self.assertFalse(self.ws4pmSettings.checkAlreadySentToPloneMeeting(document))
        self.assertNotIn(WS4PMCLIENT_ANNOTATION_KEY, annotations)

    def test_renderTALExpression(self):
        document = self.create_document()
        render = self.ws4pmSettings.renderTALExpression
        # never None, it breaks the REST calls
        self.assertEqual(render(document, self.portal, u"python: None", {}), u"")
        self.assertEqual(render(document, self.portal, u"", {}), u"")
        self.assertEqual(render(document, self.portal, u"object/Title", {}), u"Document title")
        self.assertEqual(render(document, self.portal, u'string:"My expr result"', {}), u'"My expr result"')
        self.assertEqual(render(document, self.portal, u"python: meetingConfigId",
                                {"meetingConfigId": u"plonegov-assembly"}), u"plonegov-assembly")
        # a wrong expression raises
        self.assertRaises(CompilerError, render, document, self.portal, u"u object/wrongMethodCall", {})

    def test_getMeetingConfigTitle(self):
        self.assertEqual(self.ws4pmSettings.getMeetingConfigTitle(u"plonegov-assembly"), u"PloneGov assembly")
        self.assertEqual(self.ws4pmSettings.getMeetingConfigTitle(u"unknown"), u"")


class TestSettings(WS4PMClientTestCase):

    def test_notify_configuration_changed(self):
        """Saving generated_actions generates the object_buttons actions."""
        object_buttons = self.portal.portal_actions.object_buttons
        self.settings.generated_actions = [
            {"pm_meeting_config_id": u"plonegov-assembly", "condition": u"python:True", "permissions": u"View"},
            {"pm_meeting_config_id": u"plonegov-assembly", "condition": u"python:True", "permissions": u"View"},
            {"pm_meeting_config_id": u"plonemeeting-assembly", "condition": u"python:True", "permissions": u"View"},
            {"pm_meeting_config_id": u"plonemeeting-assembly", "condition": u"python:False",
             "permissions": u"View"},
            {"pm_meeting_config_id": u"plonemeeting-assembly", "condition": u"python:True",
             "permissions": u"Manage portal"},
        ]
        action_ids = [action_id for action_id in object_buttons.objectIds() if action_id.startswith(ACTION_SUFFIX)]
        self.assertEqual(action_ids, [ACTION_SUFFIX + str(i) for i in range(1, 6)])
        action = object_buttons[ACTION_SUFFIX + "1"]
        self.assertEqual(action.title, u"Send to PloneGov assembly")
        self.assertEqual(action.url_expr, "string:${object_url}/@@send_to_plonemeeting_form"
                                          "?meetingConfigId=plonegov-assembly")
        self.assertEqual(action.icon_expr,
                         "string:${portal_url}/++resource++imio.pm.wsclient.images/send_to_plonemeeting.png")
        self.assertEqual(action.permissions, ("View",))
        self.assertTrue(action.visible)
        # 2 of the generated actions are not available to a Member
        setRoles(self.portal, TEST_USER_ID, ["Member"])
        self.request.set("URL", self.portal.absolute_url())
        self.request.set("ACTUAL_URL", self.portal.absolute_url())
        buttons = [act for act in self.portal.portal_actions.listFilteredActionsFor(self.portal)["object_buttons"]
                   if act["id"].startswith(ACTION_SUFFIX)]
        self.assertEqual(len(buttons), 3)
        # saved again with 2 actions
        self.settings.generated_actions = [
            {"pm_meeting_config_id": u"plonegov-assembly", "condition": u"python:True", "permissions": u"View"},
            {"pm_meeting_config_id": u"plonemeeting-assembly", "condition": None, "permissions": None},
        ]
        buttons = [act for act in self.portal.portal_actions.listFilteredActionsFor(self.portal)["object_buttons"]
                   if act["id"].startswith(ACTION_SUFFIX)]
        self.assertEqual(len(buttons), 2)
        self.assertIn("meetingConfigId=plonegov-assembly", buttons[0]["url"])
        self.assertIn("meetingConfigId=plonemeeting-assembly", buttons[1]["url"])
        # default permission
        self.assertEqual(object_buttons[ACTION_SUFFIX + "2"].permissions, ("View",))
        # another record or event: nothing changes
        record = getUtility(IRegistry).records[IWS4PMClientSettings.__identifier__ + ".pm_url"]
        notify_configuration_changed(RecordModifiedEvent(record, PM_URL, PM_URL))
        notify_configuration_changed(object())
        self.assertEqual(len([action_id for action_id in object_buttons.objectIds()
                              if action_id.startswith(ACTION_SUFFIX)]), 2)
