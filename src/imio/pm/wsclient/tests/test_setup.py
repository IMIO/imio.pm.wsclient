# -*- coding: utf-8 -*-
"""Installation of the default profile (F1, F13)."""
from imio.pm.wsclient.browser.settings import IWS4PMClientSettings
from imio.pm.wsclient.interfaces import IWS4PMClientLayer
from imio.pm.wsclient.testing import WS4PMClientTestCase
from plone.browserlayer.utils import registered_layers
from plone.registry.interfaces import IRegistry
from zope.component import getUtility


class TestInstall(WS4PMClientTestCase):

    def test_browserlayer(self):
        self.assertIn(IWS4PMClientLayer, registered_layers())

    def test_controlpanel(self):
        configlet = [action for action in self.portal.portal_controlpanel.listActions()
                     if action.id == "ws4pmclientsettings"][0]
        self.assertEqual(configlet.title, "WS4PM Client settings")
        self.assertEqual(configlet.permissions, ("Manage portal",))
        self.assertEqual(configlet.getActionExpression(), "string:${portal_url}/@@ws4pmclient-settings")

    def test_registry(self):
        settings = getUtility(IRegistry).forInterface(IWS4PMClientSettings)
        # defaults of the records not set by the testing layer
        self.assertEqual(settings.pm_timeout, 10)
        self.assertTrue(settings.only_one_sending)
        self.assertTrue(settings.select_all_attachments_by_default)
        self.assertEqual(settings.allowed_annexes_types, [])
        self.assertIsNone(settings.viewlet_display_condition)

    def test_rolemap(self):
        for permission in ("WS Client Access", "WS Client Send"):
            roles = [role["name"] for role in self.portal.rolesOfPermission(permission) if role["selected"]]
            self.assertEqual(sorted(roles), ["Manager", "Member"])

    def test_resources(self):
        self.assertTrue(self.portal.restrictedTraverse(
            "++resource++imio.pm.wsclient.images/send_to_plonemeeting.png"))
        self.assertTrue(self.portal.restrictedTraverse("++resource++imio.pm.wsclient.javascripts/popups.js"))

    def test_postInstall(self):
        # the import step of the default profile does nothing
        result = self.portal.portal_setup.runImportStepFromProfile(
            "profile-imio.pm.wsclient:default", "imio.pm.wsclient-postInstall", run_dependencies=False)
        self.assertEqual(result["steps"], ["imio.pm.wsclient-postInstall"])
