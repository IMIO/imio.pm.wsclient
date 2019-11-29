# -*- coding: utf-8 -*-

import base64
import logging

from zope.component import getMultiAdapter
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR, UNABLE_TO_DETECT_MIMETYPE_ERROR, \
    FILENAME_MANDATORY_ERROR, ANNEXID_MANDATORY_ERROR, MISSING_FILE_ERROR

logger = logging.getLogger('imio.pm.wsclient')


class BaseDownloadFromItemView(BrowserView):
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        self.itemUID = self.request.get('itemUID', '')

    def __call__(self):
        """ """
        # first check that we can connect to PloneMeeting
        client = self.ws4pmSettings._soap_connectToPloneMeeting()
        if not client:
            IStatusMessage(self.request).addStatusMessage(_(UNABLE_TO_CONNECT_ERROR), "error")
            return self.request.RESPONSE.redirect(self.context.absolute_url())


class GenerateItemTemplateView(BaseDownloadFromItemView):
    """
      This view manage the document generation on an item
    """
    def __init__(self, context, request):
        super(GenerateItemTemplateView, self).__init__(context, request)
        self.templateId = self.request.get('templateId', '')
        self.templateFilename = self.request.get('templateFilename', '')
        self.templateFormat = self.request.get('templateFormat', '')

    def __call__(self):
        """ """
        ws_error = super(GenerateItemTemplateView, self).__call__()
        if ws_error:
            return ws_error

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


class DownloadAnnexFromItemView(BaseDownloadFromItemView):
    """
      This view manage the annexes download on an item
    """

    def __init__(self, context, request):
        super(DownloadAnnexFromItemView, self).__init__(context, request)
        self.annex_id = self.request.get('annex_id', '')
        self.annex_type = self.request.get('annex_type', '')
        self.annex_type = self.annex_type and [self.annex_type] or []

    def __call__(self):
        """ """
        ws_error = super(DownloadAnnexFromItemView, self).__call__()
        if ws_error:
            return ws_error

        response = self.request.RESPONSE

        if not self.annex_id:
            IStatusMessage(self.request).addStatusMessage(_(ANNEXID_MANDATORY_ERROR), "error")
            return response.redirect(self.context.absolute_url())

        res = self.ws4pmSettings._soap_getItemInfos(
            {
                'UID': self.itemUID,
                'showAnnexes': True,
                'allowed_annexes_types': self.annex_type,
                'include_annex_binary': True,
            }
        )
        if not res:
            # an error occured, redirect to user to the context, a statusMessage will be displayed
            IStatusMessage(self.request).addStatusMessage(_(MISSING_FILE_ERROR), "error")
            return self.request.RESPONSE.redirect(self.context.absolute_url())

        annex_info = [anx for anx in res[0].annexes if anx.id == self.annex_id]
        if annex_info:
            annex_info = annex_info[0]
            annex = annex_info.file
            response.setHeader('Content-Type', annex_info.filename.split('.')[-1])
            response.setHeader('Content-Disposition', 'inline;filename="%s"' % annex_info.filename)
            return base64.b64decode(annex)
