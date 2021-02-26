# -*- coding: utf-8 -*-

from zope.i18nmessageid import MessageFactory


WS4PMClientMessageFactory = MessageFactory("imio.pm.wsclient")
PMMessageFactory = MessageFactory("PloneMeeting")


def initialize(context):
    """Initializer called when used as a Zope 2 product."""
