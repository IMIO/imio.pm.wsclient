# -*- coding: utf-8 -*-

from imio.pm.wsclient.interfaces import IPMWSClientEvent
from imio.pm.wsclient.interfaces import ISentToPM
from imio.pm.wsclient.interfaces import IWillbeSendToPM

from zope.component.interfaces import ObjectEvent
from zope.interface import implements


class PMWSClientEvent(ObjectEvent):
    """
      Abstract pm ws event. All pm ws events should inherit from it
    """
    implements(IPMWSClientEvent)


class WillbeSendToPM(PMWSClientEvent):
    """
      Notified when an item is about to be sent to PM.
    """
    implements(IWillbeSendToPM)


class SentToPM(PMWSClientEvent):
    """
       Notified when an item has been successfully sent to PM.
    """
    implements(ISentToPM)
