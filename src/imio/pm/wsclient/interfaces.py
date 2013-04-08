# -*- coding: utf-8 -*-
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
