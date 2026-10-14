# -*- coding: utf-8 -*-
"""browser/viewlets.py: PloneMeeting infos of a sent element (F7)."""
from imio.pm.wsclient.browser.viewlets import PloneMeetingInfosViewlet
from imio.pm.wsclient.config import CAN_NOT_SEE_LINKED_ITEMS_INFO
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from imio.pm.wsclient.testing import FAKE_PM
from imio.pm.wsclient.testing import WS4PMClientTestCase
from plone import api
from plone.app.testing import login
from zope.annotation import IAnnotations

import unittest


class TestPloneMeetingInfosViewlet(WS4PMClientTestCase):
    def setUp(self):
        super(TestPloneMeetingInfosViewlet, self).setUp()
        self.document = self.create_document()

    def viewlet(self, obj=None):
        viewlet = PloneMeetingInfosViewlet(
            obj or self.document, self.request, None, None
        )
        viewlet.update()
        return viewlet

    def test_update(self):
        self.assertEqual(
            self.viewlet().ws4pmSettings.settings().pm_url, self.settings.pm_url
        )

    def test_available(self):
        # not sent: not displayed
        viewlet = self.viewlet()
        self.assertFalse(viewlet.available())
        # a TAL condition takes precedence (memoized)
        self.settings.viewlet_display_condition = u"python: True"
        self.assertFalse(viewlet.available())
        self.clean_memoize(viewlet)
        self.assertEqual(viewlet.available(), (CAN_NOT_SEE_LINKED_ITEMS_INFO, "info"))
        # sent, displayed by default
        self.settings.viewlet_display_condition = u""
        item = self.send_to_pm(self.document)
        self.clean_memoize(viewlet)
        self.assertTrue(viewlet.available() is True)
        # a TAL condition using isLinked
        self.settings.viewlet_display_condition = (
            u'python: isLinked and object.portal_type == "wrong_value"'
        )
        self.clean_memoize(viewlet)
        self.assertFalse(viewlet.available())
        self.settings.viewlet_display_condition = (
            u'python: isLinked and object.portal_type == "Document"'
        )
        self.clean_memoize(viewlet)
        self.assertTrue(viewlet.available() is True)
        # a wrong TAL condition: an error message
        self.settings.viewlet_display_condition = (
            u"python: object.getUnexistingAttribute()"
        )
        self.clean_memoize(viewlet)
        message, level = viewlet.available()
        self.assertEqual(level, "error")
        self.assertTrue(
            message.startswith(
                u"Unable to display informations about the potentially linked item"
            )
        )
        # PloneMeeting can not be reached: an error message, the element is still linked
        self.settings.viewlet_display_condition = u""
        self.settings.pm_url = u"http://wrong/url"
        self.clean_memoize(viewlet)
        self.assertEqual(viewlet.available(), (UNABLE_TO_CONNECT_ERROR, "error"))
        self.assertEqual(
            IAnnotations(self.document)[WS4PMCLIENT_ANNOTATION_KEY],
            ["plonemeeting-assembly"],
        )
        # the item was deleted in PloneMeeting
        self.settings.pm_url = FAKE_PM.url
        FAKE_PM.items.remove(item)
        self.clean_memoize(viewlet)
        self.assertFalse(viewlet.available())

    def test_get_item_info(self):
        item = self.send_to_pm(self.document)
        info = self.viewlet().get_item_info({"UID": item["UID"]})
        self.assertEqual(info["UID"], item["UID"])
        self.assertEqual(
            info["extra_include_config"],
            {"id": u"plonemeeting-assembly", "title": u"PloneMeeting assembly"},
        )
        self.assertEqual(
            info["review_state"], {"token": u"itemcreated", "title": u"Created"}
        )
        self.assertEqual(info["extra_include_meeting"], {})
        self.assertEqual(info["extra_include_annexes"], [])
        self.assertEqual(
            [template["id"] for template in info["extra_include_pod_templates"]],
            [u"itemTemplate"],
        )

    def test_getPloneMeetingLinkedInfos(self):
        item = self.send_to_pm(self.document)
        viewlet = self.viewlet()
        self.assertEqual(
            [info["UID"] for info in viewlet.getPloneMeetingLinkedInfos()],
            [item["UID"]],
        )
        # sent inTheNameOf pmCreator1, who sees it
        login(self.portal, "pmCreator1")
        self.clean_memoize(viewlet)
        self.assertEqual(
            [info["UID"] for info in viewlet.getPloneMeetingLinkedInfos()],
            [item["UID"]],
        )
        # pmCreator2 only gets a message
        login(self.portal, "pmCreator2")
        self.clean_memoize(viewlet)
        self.assertEqual(
            viewlet.getPloneMeetingLinkedInfos(),
            (CAN_NOT_SEE_LINKED_ITEMS_INFO, "info"),
        )
        # linked items (delayed item), the last created first
        successor_1 = FAKE_PM.add_item(
            u"plonemeeting-assembly", u"developers", u"pmCreator1", title=u"Successor 1"
        )
        successor_2 = FAKE_PM.add_item(
            u"plonegov-assembly", u"developers", u"pmCreator1", title=u"Successor 2"
        )
        item["successors"] = [successor_1["UID"]]
        successor_1["successors"] = [successor_2["UID"]]
        login(self.portal, "pmCreator1")
        self.clean_memoize(viewlet)
        self.assertEqual(
            [info["id"] for info in viewlet.getPloneMeetingLinkedInfos()],
            [u"successor-2", u"successor-1", u"document-title"],
        )
        # an item of PloneMeeting linked to the element but not in its annotation (sent by PloneMeeting)
        FAKE_PM.add_item(
            u"plonegov-assembly",
            u"developers",
            u"pmCreator1",
            title=u"Sent",
            externalIdentifier=self.document.UID(),
        )
        self.clean_memoize(viewlet)
        self.assertEqual(len(viewlet.getPloneMeetingLinkedInfos()), 4)
        self.assertEqual(
            IAnnotations(self.document)[WS4PMCLIENT_ANNOTATION_KEY],
            ["plonemeeting-assembly", "plonegov-assembly"],
        )

    @unittest.expectedFailure
    def test_getPloneMeetingLinkedInfos_hidden_config(self):
        """Master bug: sent to 2 configs but the user only sees 1 item: the special
        result of the hidden config has no 'created' and the sort raises KeyError."""
        self.send_to_pm(self.document)
        self.send_to_pm(
            self.document,
            "plonegov-assembly",
            **{"form.widgets.category": [u"deployment"]}
        )
        FAKE_PM.items[-1]["proposingGroup"] = u"vendors"
        login(self.portal, "pmCreator1")
        infos = self.viewlet().getPloneMeetingLinkedInfos()
        self.assertEqual(
            infos[-1],
            {
                "extra_include_config": {
                    "id": "plonegov-assembly",
                    "title": u"PloneGov assembly",
                }
            },
        )

    def test_displayMeetingDate(self):
        viewlet = self.viewlet(self.portal)
        self.assertEqual(viewlet.displayMeetingDate(""), "-")
        self.assertEqual(viewlet.displayMeetingDate(None), "-")
        self.assertEqual(viewlet.displayMeetingDate("2013-06-10"), u"2013-06-10")
        self.assertEqual(
            viewlet.displayMeetingDate("2013-06-10 (15:30)"), u"2013-06-10 (15:30)"
        )

    def test_render(self):
        # not sent: nothing
        self.assertEqual(self.viewlet().render().strip(), u"")
        # the item with its annexes and documents
        folder = api.content.create(container=self.portal, type="Folder", title=u"Mail")
        self.create_file(folder)
        item = self.send_to_pm(
            folder, **{"form.widgets.annexes": [folder.objectValues()[0].UID()]}
        )
        html = self.viewlet(folder).render()
        self.assertIn(u"PloneMeeting informations", html)
        self.assertIn(u'href="{0}"'.format(item["@id"]), html)
        self.assertIn(u">Mail</a>", html)
        self.assertIn(u"M. PMCreator One", html)
        self.assertIn(u"PloneMeeting assembly", html)
        self.assertIn(u"Created", html)
        self.assertIn(
            u"{0}/@@download_annex_from_plonemeeting?itemUID={1}&amp;annex_id=annexe-oubliee.txt".format(
                folder.absolute_url(), item["UID"]
            ),
            html,
        )
        self.assertIn(
            u"{0}/@@generate_document_from_plonemeeting?itemUID={1}&amp;templateId=itemTemplate__format__"
            u"odt&amp;templateFilename=itemTemplate&amp;templateFormat=odt".format(
                folder.absolute_url(), item["UID"]
            ),
            html,
        )
        # an error message
        self.settings.pm_url = u"http://wrong/url"
        self.clean_memoize()
        html = self.viewlet(folder).render()
        self.assertIn(u"portalMessage error", html)
        self.assertIn(UNABLE_TO_CONNECT_ERROR, html)

    @unittest.expectedFailure
    def test_render_can_not_see(self):
        """Master bug: a user who can not see the linked item gets a LocationError
        (item/extraInfos) instead of the CAN_NOT_SEE_LINKED_ITEMS_INFO message."""
        self.send_to_pm(self.document)
        login(self.portal, "pmCreator2")
        html = self.viewlet().render()
        self.assertIn(u"portalMessage info", html)
        self.assertIn(CAN_NOT_SEE_LINKED_ITEMS_INFO, html)
