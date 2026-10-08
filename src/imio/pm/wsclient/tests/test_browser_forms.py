# -*- coding: utf-8 -*-
"""browser/forms.py: the send form (F5, F6)."""
from AccessControl import Unauthorized
from datetime import datetime
from imio.pm.wsclient.config import ALREADY_SENT_TO_PM_ERROR
from imio.pm.wsclient.config import CORRECTLY_SENT_TO_PM_INFO
from imio.pm.wsclient.config import NO_PROPOSING_GROUP_ERROR
from imio.pm.wsclient.config import (
    SEND_WITHOUT_SUFFICIENT_FIELD_MAPPINGS_DEFINED_WARNING,
)
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from imio.pm.wsclient.interfaces import ISentToPMEvent
from imio.pm.wsclient.interfaces import IWillbeSendToPMEvent
from imio.pm.wsclient.testing import FAKE_PM
from imio.pm.wsclient.testing import WS4PMClientTestCase
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME
from zope.annotation import IAnnotations
from zope.component import getGlobalSiteManager
from zope.i18n import translate
from zope.interface import Interface

import base64
import unittest


class TestDisplayDataToSendProvider(WS4PMClientTestCase):
    def provider(self, obj):
        view = self.send_form(obj)
        view.update()
        return view.widgets["dataToSend"]

    def test_getDisplayableData(self):
        document = self.create_document()
        data = self.provider(document).getDisplayableData()
        # no externalIdentifier, annexes nor empty values, but category and proposingGroup
        self.assertEqual(sorted(data), ["category", "decision", "description", "title"])
        self.assertEqual(data["title"], u"Document title")
        self.assertEqual(data["category"], u"")
        self.assertEqual(self.messages(), [])
        # extraAttrs and no title mapping
        self.settings.field_mappings = [
            {
                "field_name": u"extraAttrs",
                "expression": u"python: [{'key': 'internalNotes', 'value': '<p>Notes</p>'}]",
            }
        ]
        data = self.provider(document).getDisplayableData()
        self.assertEqual(
            data["extraAttrs"],
            "<fieldset><legend>PloneMeeting_label_internalNotes</legend><p>Notes</p></fieldset>",
        )
        self.assertEqual(
            self.messages(), [SEND_WITHOUT_SUFFICIENT_FIELD_MAPPINGS_DEFINED_WARNING]
        )

    def test_render(self):
        html = self.provider(self.create_document()).render()
        self.assertIn(u"Here is a resume of what will be sent to PloneMeeting", html)
        self.assertIn(u"Document title", html)
        self.assertIn(u"<p>Document description</p>", html)


class TestSendToPloneMeetingForm(WS4PMClientTestCase):
    def setUp(self):
        super(TestSendToPloneMeetingForm, self).setUp()
        self.document = self.create_document()

    def test___init__(self):
        view = self.send_form(self.document, "plonegov-assembly")
        self.assertEqual(view.label, u"Send to PloneGov assembly")
        self.assertEqual(view.meetingConfigId, "plonegov-assembly")
        self.assertEqual(view.proposingGroupId, "")
        # only for authenticated users
        logout()
        self.assertRaises(Unauthorized, self.send_form, self.document)
        login(self.portal, "pmCreator1")
        self.assertEqual(
            self.send_form(self.document).label, u"Send to PloneMeeting assembly"
        )

    def test_handleSendToPloneMeeting(self):
        # the form is shown, nothing is sent
        html = self.send_form(self.document)()
        self.assertIn("form-buttons-send_to_plonemeeting", html)
        self.assertIn("Developers", html)
        self.assertEqual(FAKE_PM.items, [])
        # the proposing group is required
        view = self.send_form(self.document)
        self.request.form["form.buttons.send_to_plonemeeting"] = u"Send"
        self.assertIn("There were some errors.", view())
        self.assertEqual(FAKE_PM.items, [])
        self.clean_form()
        # sent
        item = self.send_to_pm(self.document)
        self.assertEqual(self.messages(), [CORRECTLY_SENT_TO_PM_INFO])
        self.assertEqual(item["creator"], u"pmCreator1")
        self.assertEqual(item["proposingGroup"], u"developers")
        self.assertEqual(item["title"], u"Document title")
        self.assertEqual(item["description"], u"Document description")
        self.assertEqual(item["decision"], u"<p>Document description</p>")
        self.assertEqual(item["category"], u"")
        self.assertEqual(item["annexes"], [])
        self.assertEqual(
            IAnnotations(self.document)[WS4PMCLIENT_ANNOTATION_KEY],
            ["plonemeeting-assembly"],
        )
        self.assertEqual(
            self.request.response.getHeader("location"),
            "{0}/@@redirect_view?url={1}".format(
                self.portal.absolute_url(), self.document.absolute_url()
            ),
        )
        # with a category, a preferred meeting and the files of a folder
        folder = api.content.create(container=self.portal, type="Folder", title=u"Mail")
        annex = self.create_file(folder)
        meeting = FAKE_PM.add_meeting(u"plonegov-assembly", datetime(2013, 3, 3))
        item = self.send_to_pm(
            folder,
            "plonegov-assembly",
            **{
                "form.widgets.category": [u"deployment"],
                "form.widgets.preferredMeeting": [meeting["UID"]],
                "form.widgets.annexes": [annex.UID()],
            }
        )
        self.assertEqual(item["category"], u"deployment")
        self.assertEqual(item["preferredMeeting"], meeting["UID"])
        self.assertEqual(
            [annex_info["id"] for annex_info in item["annexes"]],
            [u"annexe-oubliee.txt"],
        )
        self.assertEqual(
            FAKE_PM.files[item["annexes"][0]["file"]["download"]], b"hello\n"
        )

    def test_handleCancel(self):
        self.request.form["form.buttons.cancel"] = "Cancel"
        self.assertEqual(self.send_form(self.document)(), "")
        self.assertEqual(FAKE_PM.items, [])
        self.assertEqual(
            self.request.response.getHeader("location"),
            "{0}/@@redirect_view?url={1}".format(
                self.portal.absolute_url(), self.document.absolute_url()
            ),
        )
        # in the overlay
        self.request.response.setStatus(200)
        self.request.form["ajax_load"] = "1234"
        self.assertEqual(self.send_form(self.document)(), "")
        self.assertEqual(
            self.request.response.getHeader("location"),
            "{0}/@@redirect_view?ajax_load=1234&url={1}".format(
                self.portal.absolute_url(), self.document.absolute_url()
            ),
        )

    def test_update(self):
        view = self.send_form(self.document)
        view.update()
        self.assertIn("standalone", view.actions["cancel"].klass)
        # PloneMeeting can not be reached
        self.settings.pm_password = u"wrongPassword"
        self.clean_memoize()
        self.assertEqual(self.send_form(self.document)(), "")
        self.assertEqual(self.messages(), [UNABLE_TO_CONNECT_ERROR])
        # in the overlay, only the messages are shown
        self.request.form["ajax_load"] = "1234"
        html = self.send_form(self.document)()
        self.assertNotIn("form-widgets-proposingGroup", html)
        self.assertEqual(self.messages(), [UNABLE_TO_CONNECT_ERROR])
        del self.request.form["ajax_load"]
        self.settings.pm_password = u"Meeting_12"
        self.clean_memoize()
        # set by the vocabularies, for this request
        del self.request.other["error_in_vocabularies"]
        # the user is unknown in PloneMeeting
        users = dict(FAKE_PM.users)
        del FAKE_PM.users[u"pmCreator1"]
        self.assertEqual(self.send_form(self.document)(), "")
        self.assertEqual(
            self.messages(),
            [u"Could not get userInfos in PloneMeeting for user 'pmCreator1'!"],
        )
        del self.request.other["error_in_vocabularies"]
        # the user is not a creator: no proposing group to choose
        FAKE_PM.users = users
        FAKE_PM.users[u"pmCreator1"]["groups"] = []
        self.clean_memoize()
        view = self.send_form(self.document)
        view.update()
        self.assertEqual(len(view.widgets["proposingGroup"].terms), 0)
        self.assertEqual(self.messages(), [])
        FAKE_PM.users[u"pmCreator1"]["groups"] = [u"developers_creators"]
        self.clean_memoize()
        # the URL of an action that is not available to the user
        self.assertRaises(
            Unauthorized, self.send_form(self.document, "wrong-meeting-config-id")
        )
        login(self.portal, "pmCreator1")
        self.assertRaises(
            Unauthorized, self.send_form(self.document, "plonegov-assembly")
        )
        self.assertIn(
            "form-buttons-send_to_plonemeeting", self.send_form(self.document)()
        )
        # already sent, the form is only shown again if an element can be sent several times
        login(self.portal, TEST_USER_NAME)
        self.send_to_pm(self.document)
        self.messages()
        self.assertEqual(self.send_form(self.document)(), "")
        self.assertEqual(self.messages(), [ALREADY_SENT_TO_PM_ERROR])
        self.settings.only_one_sending = False
        self.assertIn(
            "form-buttons-send_to_plonemeeting", self.send_form(self.document)()
        )
        self.assertEqual(self.messages(), [])

    def test_check_if_all_annexes_selection(self):
        view = self.send_form(self.document)
        self.assertTrue(view.check_if_all_annexes_selection())
        self.settings.select_all_attachments_by_default = False
        self.assertFalse(view.check_if_all_annexes_selection())

    def test_updateWidgets(self):
        view = self.send_form(self.document)
        view.update()
        self.assertEqual(view.widgets["meetingConfigId"].mode, "hidden")
        self.assertEqual(view.widgets["meetingConfigId"].value, "plonemeeting-assembly")
        self.assertTrue(view.widgets["proposingGroup"].prompt)
        # no category in plonemeeting-assembly, no annex for a document
        self.assertEqual(view.widgets["category"].mode, "hidden")
        self.assertFalse(view.widgets["category"].field.required)
        self.assertEqual(view.widgets["annexes"].mode, "hidden")
        # the category forced by the field mappings, the files of a folder selected by default
        folder = api.content.create(container=self.portal, type="Folder", title=u"Mail")
        annexes = [
            self.create_file(folder, title=title) for title in (u"Annex 1", u"Annex 2")
        ]
        view = self.send_form(folder, "plonegov-assembly")
        view.update()
        self.assertEqual(view.widgets["category"].mode, "input")
        self.assertTrue(view.widgets["category"].field.required)
        self.assertEqual(
            [term.value for term in view.widgets["category"].terms], [u"deployment"]
        )
        self.assertEqual(view.widgets["annexes"].mode, "input")
        self.assertEqual(
            view.widgets["annexes"].value, [annex.UID() for annex in annexes]
        )
        self.settings.select_all_attachments_by_default = False
        view = self.send_form(folder, "plonegov-assembly")
        view.update()
        self.assertFalse(view.widgets["annexes"].value)

    def test_render(self):
        view = self.send_form(self.document)
        view.update()
        self.assertIn("form-buttons-send_to_plonemeeting", view.render())
        view._finishedSent = True
        self.assertEqual(view.render(), "")
        self.assertEqual(
            self.request.response.getHeader("location"),
            "{0}/@@redirect_view?url={1}".format(
                self.portal.absolute_url(), self.document.absolute_url()
            ),
        )

    def test__findMeetingConfigId(self):
        view = self.send_form(self.document, "plonegov-assembly")
        self.assertEqual(view._findMeetingConfigId(), "plonegov-assembly")
        # when the form is submitted
        self.request.set("meetingConfigId", "")
        self.request.form["form.widgets.meetingConfigId"] = "plonemeeting-assembly"
        self.assertEqual(view._findMeetingConfigId(), "plonemeeting-assembly")

    def test__doSendToPloneMeeting(self):
        events = []

        def handler(obj, event):
            events.append((event, obj, view._finishedSent, len(FAKE_PM.items)))

        view = self.send_form(self.document)
        view.proposingGroupId = u"developers"
        gsm = getGlobalSiteManager()
        gsm.registerHandler(handler, (Interface, IWillbeSendToPMEvent))
        gsm.registerHandler(handler, (Interface, ISentToPMEvent))
        try:
            self.assertTrue(view._doSendToPloneMeeting())
        finally:
            gsm.unregisterHandler(handler, (Interface, IWillbeSendToPMEvent))
            gsm.unregisterHandler(handler, (Interface, ISentToPMEvent))
        # WillbeSendToPMEvent before sending, SentToPMEvent after
        self.assertTrue(IWillbeSendToPMEvent.providedBy(events[0][0]))
        self.assertEqual(events[0][1:], (self.document, False, 0))
        self.assertTrue(ISentToPMEvent.providedBy(events[1][0]))
        self.assertEqual(events[1][1:], (self.document, True, 1))
        self.assertEqual(self.messages(), [CORRECTLY_SENT_TO_PM_INFO])
        # sent only once
        self.assertFalse(view._doSendToPloneMeeting())
        self.assertEqual(len(FAKE_PM.items), 1)
        # or several times
        self.settings.only_one_sending = False
        self.assertTrue(view._doSendToPloneMeeting())
        self.assertEqual(
            IAnnotations(self.document)[WS4PMCLIENT_ANNOTATION_KEY],
            ["plonemeeting-assembly", "plonemeeting-assembly"],
        )
        # a proposing group the user can not use: PloneMeeting refuses the item
        view.proposingGroupId = u"vendors"
        self.assertFalse(view._doSendToPloneMeeting())
        self.assertEqual(self.messages()[-1], translate(NO_PROPOSING_GROUP_ERROR))
        self.assertEqual(len(FAKE_PM.items), 2)

    @unittest.expectedFailure
    def test__doSendToPloneMeeting_warnings(self):
        """Master bug: the warnings of PloneMeeting are never shown to a Manager ('@warnings' in the answer)."""
        self.settings.field_mappings = list(self.settings.field_mappings) + [
            {"field_name": u"ignore_validation_for", "expression": u"string:category"}
        ]
        view = self.send_form(self.document, "plonegov-assembly")
        view.proposingGroupId = u"developers"
        self.assertTrue(view._doSendToPloneMeeting())
        self.assertIn(
            u"Validation was ignored for following fields: category.", self.messages()
        )

    def test__getCreationData(self):
        view = self.send_form(self.document)
        data = view._getCreationData(None)
        self.assertEqual(
            data,
            {
                "__children__": [],
                "category": u"",
                "decision": u"<p>Document description</p>",
                "description": u"Document description",
                "externalIdentifier": self.document.UID(),
                "title": u"Document title",
            },
        )

    def test__buildDataDict(self):
        view = self.send_form(self.document)
        self.request.form.update(
            {
                "form.widgets.preferredMeeting": ["--NOVALUE--"],
                "form.widgets.category": ["--NOVALUE--"],
            }
        )
        data = view._buildDataDict()
        self.assertEqual(
            list(data),
            [
                "__children__",
                "category",
                "title",
                "description",
                "decision",
                "externalIdentifier",
            ],
        )
        self.assertEqual(data["category"], u"")
        # the category of the form when the config uses categories, a preferred meeting
        view = self.send_form(self.document, "plonegov-assembly")
        self.request.form.update(
            {
                "form.widgets.preferredMeeting": ["meeting-uid"],
                "form.widgets.category": ["deployment"],
            }
        )
        data = view._buildDataDict()
        self.assertEqual(data["preferredMeeting"], "meeting-uid")
        self.assertEqual(data["category"], "deployment")

    @unittest.expectedFailure
    def test__buildDataDict_wrong_expression(self):
        """Master bug: on a TAL error, _buildDataDict returns the redirect URL instead of
        the data and the form crashes (TypeError in DisplayDataToSendProvider)."""
        self.settings.field_mappings = [
            {"field_name": u"title", "expression": u"python: object.unknown()"}
        ]
        self.send_form(self.document)()
        self.assertIn(
            u"There was an error evaluating the TAL expression 'python: object.unknown()' for "
            u"the field 'title'!",
            self.messages()[0],
        )

    def test__buildAnnexesData(self):
        folder = api.content.create(container=self.portal, type="Folder", title=u"Mail")
        annex = self.create_file(folder)
        view = self.send_form(folder)
        self.assertEqual(view._buildAnnexesData(), [])
        self.request.form["form.widgets.annexes"] = [annex.UID(), "unknown-uid"]
        self.assertEqual(
            view._buildAnnexesData(),
            [
                {
                    "@type": "annex",
                    "title": u"Annexe oubliee",
                    "file": {
                        "filename": u"annexe oubliee.txt",
                        "data": base64.b64encode(b"hello\n").decode("ascii"),
                    },
                }
            ],
        )

    def test__getCategoriesVocab(self):
        self.assertEqual(len(self.send_form(self.document)._getCategoriesVocab()), 0)
        view = self.send_form(self.document, "plonegov-assembly")
        self.assertEqual(
            [term.value for term in view._getCategoriesVocab()], [u"deployment"]
        )

    def test__getProposingGroupsVocab(self):
        view = self.send_form(self.document)
        self.assertEqual(
            [term.title for term in view._getProposingGroupsVocab()], [u"Developers"]
        )

    def test__changeFormForErrors(self):
        view = self.send_form(self.document)
        view._changeFormForErrors()
        self.assertTrue(view._finishedSent)
        # in the overlay, the messages are shown in place of the form
        self.request.form["ajax_load"] = "1234"
        view = self.send_form(self.document)
        view._changeFormForErrors()
        self.assertFalse(view._finishedSent)
        self.assertNotIn("form-widgets-proposingGroup", view.render())
