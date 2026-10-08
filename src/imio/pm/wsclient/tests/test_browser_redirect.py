# -*- coding: utf-8 -*-
"""browser/redirect.py: redirection out of the overlay (F10)."""
from imio.pm.wsclient.interfaces import IRedirect
from imio.pm.wsclient.testing import WS4PMClientTestCase


class TestRedirectView(WS4PMClientTestCase):

    def test___call__(self):
        document = self.create_document()
        self.request.form["url"] = document.absolute_url()
        view = self.portal.restrictedTraverse("@@redirect_view")
        self.assertIsNone(view())
        self.assertEqual(self.request.response.getHeader("location"), document.absolute_url())
        # in the overlay, the page gives the URL to go to
        self.request.form["ajax_load"] = "1234"
        self.assertEqual(view(), '<html><head><base href="{0}" /></head></html>'.format(document.absolute_url()))


class TestRedirect(WS4PMClientTestCase):

    def test_redirect(self):
        IRedirect(self.request).redirect("http://nohost/plone/document")
        self.assertEqual(self.request.response.getHeader("location"),
                         "http://nohost/plone/@@redirect_view?url=http://nohost/plone/document")
        self.request.form["ajax_load"] = "1234"
        IRedirect(self.request).redirect("http://nohost/plone/document")
        self.assertEqual(self.request.response.getHeader("location"),
                         "http://nohost/plone/@@redirect_view?ajax_load=1234&url=http://nohost/plone/document")
