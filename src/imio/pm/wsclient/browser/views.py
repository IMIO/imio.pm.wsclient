# -*- coding: utf-8 -*-

import base64
import logging

from zope.component import getMultiAdapter
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR, UNABLE_TO_DETECT_MIMETYPE_ERROR, \
    FILENAME_MANDATORY_ERROR

logger = logging.getLogger('imio.pm.wsclient')


class GenerateItemTemplateView(BrowserView):
    """
      This view manage the document generation on an item
    """
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        self.itemUID = self.request.get('itemUID', '')
        self.templateId = self.request.get('templateId', '')
        self.templateFilename = self.request.get('templateFilename', '')
        self.templateFormat = self.request.get('templateFormat', '')

    def __call__(self):
        """ """
        # first check that we can connect to PloneMeeting
        client = self.ws4pmSettings._soap_connectToPloneMeeting()
        if not client:
            IStatusMessage(self.request).addStatusMessage(_(UNABLE_TO_CONNECT_ERROR), "error")
            return self.request.RESPONSE.redirect(self.context.absolute_url())

        # if we can connect, proceed!
        response = self.request.RESPONSE
        mimetype = self.portal.mimetypes_registry.lookupExtension(self.templateFormat)
        if not mimetype:
            IStatusMessage(self.request).addStatusMessage(_(UNABLE_TO_DETECT_MIMETYPE_ERROR), "error")
            return response.redirect(self.context.absolute_url())

        if not self.templateFilename:
            IStatusMessage(self.request).addStatusMessage(_(FILENAME_MANDATORY_ERROR), "error")
            return response.redirect(self.context.absolute_url())

        # set relevant header for response so the browser behave normally with returned file type
        response.setHeader('Content-Type', mimetype.normalized())
        response.setHeader('Content-Disposition', 'inline;filename="%s.%s"' % (self.templateFilename,
                                                                               self.templateFormat))

        res = self.ws4pmSettings._soap_getItemTemplate({'itemUID': self.itemUID,
                                                        'templateId': self.templateId, })
        if not res:
            # an error occured, redirect to user to the context, a statusMessage will be displayed
            return self.request.RESPONSE.redirect(self.context.absolute_url())

        return base64.b64decode(res)
