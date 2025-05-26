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

    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile('imio.pm.wsclient:default', 'rolemap')

    logger.info("upgrade step done!")
