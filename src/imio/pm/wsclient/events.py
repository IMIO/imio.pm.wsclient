# -*- coding: utf-8 -*-

from imio.pm.wsclient.interfaces import IPMWSClientEvent
from imio.pm.wsclient.interfaces import ISentToPMEvent
from imio.pm.wsclient.interfaces import IWillbeSendToPMEvent
from zope.component.interfaces import ObjectEvent
from zope.interface import implements


class PMWSClientEvent(ObjectEvent):
    """
      Abstract pm ws event. All pm ws events should inherit from it
    """
    implements(IPMWSClientEvent)


class WillbeSendToPMEvent(PMWSClientEvent):
    """
      Notified when an item is about to be sent to PM.
    """
    implements(IWillbeSendToPMEvent)


class SentToPMEvent(PMWSClientEvent):
    """
       Notified when an item has been successfully sent to PM.
    """
    implements(ISentToPMEvent)
