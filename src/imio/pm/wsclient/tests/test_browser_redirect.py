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
        self.assertEqual(
            self.request.response.getHeader("location"), document.absolute_url()
        )
        # in the overlay, the page gives the URL to go to
        self.request.form["ajax_load"] = "1234"
        self.assertEqual(
            view(),
            '<html><head></head><body data-base-url="{0}" data-view-url="{0}"></body></html>'.format(
                document.absolute_url()
            ),
        )
        # the url is escaped in the page and must be in the portal
        self.request.form["url"] = document.absolute_url() + "?a=1&b=2"
        self.assertIn(
            'data-view-url="{0}?a=1&amp;b=2"'.format(document.absolute_url()), view()
        )
        for url in (
            "http://evil.example.org/plone",
            "javascript:alert(1)",
            document.absolute_url() + '?a="><script>alert(1)</script>',
            "",
        ):
            self.request.form["url"] = url
            self.assertIn('data-view-url="http://nohost/plone"', view())
        del self.request.form["ajax_load"]
        self.request.form["url"] = "http://evil.example.org/plone"
        view()
        self.assertEqual(
            self.request.response.getHeader("location"), "http://nohost/plone"
        )


class TestRedirect(WS4PMClientTestCase):
    def test_redirect(self):
        IRedirect(self.request).redirect("http://nohost/plone/document")
        self.assertEqual(
            self.request.response.getHeader("location"),
            "http://nohost/plone/@@redirect_view?url=http://nohost/plone/document",
        )
        self.request.form["ajax_load"] = "1234"
        IRedirect(self.request).redirect("http://nohost/plone/document")
        self.assertEqual(
            self.request.response.getHeader("location"),
            "http://nohost/plone/@@redirect_view?ajax_load=1234&url=http://nohost/plone/document",
        )
        # the Plone 6 modal posts the form by XHR without ajax_load
        del self.request.form["ajax_load"]
        self.request.environ["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
        IRedirect(self.request).redirect("http://nohost/plone/document")
        self.assertEqual(
            self.request.response.getHeader("location"),
            "http://nohost/plone/@@redirect_view?ajax_load=1&url=http://nohost/plone/document",
        )
