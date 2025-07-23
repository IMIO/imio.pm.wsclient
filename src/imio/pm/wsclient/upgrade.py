# -*- coding: utf-8 -*-

from plone import api

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
