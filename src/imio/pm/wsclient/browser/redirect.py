# -*- coding: utf-8 -*-

from imio.pm.wsclient.interfaces import IRedirect
from Products.Five import BrowserView
from zope.component.hooks import getSite
from zope.interface import implementer


class RedirectView(BrowserView):
    """ """

    DEFAULT = """<html><head></head><body data-base-url="{0}" data-view-url="{0}"></body></html>"""

    def __call__(self):
        """ """
        url = self.request.form.get("url", "")
        if "ajax_load" in self.request.form:
            return self.DEFAULT.format(url)
        else:
            self.request.RESPONSE.redirect(url)


@implementer(IRedirect)
class Redirect(object):
    """ """

    def __init__(self, request):
        self.request = request
        # the Plone 6 modal posts the form by XHR without ajax_load
        self.ajax_load = self.request.form.get("ajax_load", "") or (
            self.request.getHeader("X-Requested-With") == "XMLHttpRequest" and "1" or ""
        )

    def redirect(self, url):
        """
        See docstring in interfaces.IRedirect
        """
        portal = getSite()
        result = []
        result.append(portal.absolute_url())
        result.append("/@@redirect_view?")
        if self.ajax_load:
            result.append("ajax_load=%s&" % self.ajax_load)
        result.append("url=%s" % url)
        self.request.RESPONSE.redirect("".join(result))
