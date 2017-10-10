# -*- coding: utf-8 -*-
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserRequest


class IWS4PMClientLayer(IBrowserRequest):
    """
      Define a layer so the element of the WS4PM client are only available when the BrowserLayer is installed
    """


class IRedirect(Interface):
    """
    """
    def redirect():
        """
          Redirect to the right place in case we use plone.app.jquerytools overlays
        """


#
# Events interfaces
#

class IPMWSClientEvent(IObjectEvent):
    """
      All pm ws events should inherit from this class
    """


class IWillbeSendToPMEvent(IPMWSClientEvent):
    """
      An item will be send to pm.
    """


class ISentToPMEvent(IPMWSClientEvent):
    """
      An item has been sent to pm.
    """


class ISendableAnnexesToPM(Interface):
    """
    Adapts a context into a list of annexes to send to pm
    """
    def get():
        """
        Return a list of dicts representing annexes following the format:
        [
            ...,
            {
                'title': <str>,
                'UID': <UID>,
            },
            ...,
        ]
        """


class IPreferredMeetings(Interface):
    """
    Adapts a context and a list of possible meetings to filter them.
    """
    def get():
        """
        Return a list of dicts representing meeting UID's and dates following the format:
        [
            ...,
            {
                'UID': <UID>,
                'date': <str>,
            },
            ...,
        ]
        """
