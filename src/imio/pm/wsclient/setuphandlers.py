# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# Copyright (c) 2013 by Imio
#
# GNU General Public License (GPL)
#

import logging


logger = logging.getLogger('imio.pm.wsclient: setuphandlers')

__author__ = """Gauthier Bastien <gauthier@imio.be>"""
__docformat__ = 'plaintext'


def isNotImioPmWsClientProfile(context):
    return context.readDataFile("imio_pm_wsclient_marker.txt") is None


def postInstall(context):
    """Called as at the end of the setup process. """
    # the right place for your custom code
    if isNotImioPmWsClientProfile(context):
        return
