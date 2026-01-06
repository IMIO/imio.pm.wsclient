# -*- coding: utf-8 -*-

from plone import api
from plone.registry import Record
from plone.registry.field import Bool
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import logging


def upgrade_to_200(context):
    logger = logging.getLogger("imio.pm.wsclient: Upgrade to REST API")
    logger.info("starting upgrade steps")
    url = api.portal.get_registry_record(
        "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.pm_url",
        default=None,
    )
    if url:
        parts = url.split("ws4pm.wsdl")
        api.portal.set_registry_record(
            "imio.pm.wsclient.browser.settings.IWS4PMClientSettings.pm_url",
            parts[0],
        )
    action_generated = api.portal.get_registry_record("imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions")
    for action in action_generated:
        if action["permissions"] == "SOAP Client Send":
            action["permissions"] = "WS Client Send"
        if action["permissions"] == "SOAP Client Access":
            action["permissions"] = "WS Client Access"
    api.portal.set_registry_record("imio.pm.wsclient.browser.settings.IWS4PMClientSettings.generated_actions", action_generated)
    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile('imio.pm.wsclient:default', 'rolemap')

    logger.info("upgrade step done!")


def upgrade_js_ressources(context):
    logger = logging.getLogger("imio.pm.wsclient: Upgrade JS ressources")
    logger.info("starting upgrade steps")
    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile("imio.pm.wsclient:default", "jsregistry")
    logger.info("upgrade step done!")


def add_new_settings_in_registry(context):
    logger = logging.getLogger("imio.pm.wsclient: Add new settings in registry")
    logger.info("starting upgrade steps")
    key = (
        "imio.pm.wsclient.browser.settings.IWS4PMClientSettings."
        "select_all_attachments_by_default"
    )
    registry = getUtility(IRegistry)
    if key in registry:
        return
    attributes = {
        "title": u"Select all attachments by default",
        "description": (
            u"When enabled, all attachments are selected by default. "
            "Users can still manually deselect individual attachments if needed."
        ),
    }
    registry_field = Bool(**attributes)
    registry_record = Record(registry_field)
    registry_record.value = True
    registry.records[key] = registry_record
    logger.info("upgrade step done!")
