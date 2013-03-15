from collections import OrderedDict
import base64
import logging
logger = logging.getLogger('imio.pm.wsclient')

from AccessControl import Unauthorized
from zope.component import getMultiAdapter
from zope.annotation import IAnnotations
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import DEFAULT_NO_WARNING_MESSAGE, WS4PMCLIENT_ANNOTATION_KEY, \
    UNABLE_TO_CONNECT_ERROR, ALREADY_SENT_TO_PM_ERROR, CORRECTLY_SENT_TO_PM_INFO, UNABLE_TO_DETECT_MIMETYPE_ERROR, \
    FILENAME_MANDATORY_ERROR, TAL_EVAL_FIELD_ERROR, NO_PROPOSING_GROUP_ERROR


class SendToPloneMeetingView(BrowserView):
    """
      This manage the action that sends the element to PloneMeeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.meetingConfigId = self.request.get('meetingConfigId', '')
        self.proposingGroupId = self.request.get('proposingGroupId', '')
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()
        self.ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')

    def __call__(self):
        """ """
        # use checkAlreadySentToPloneMeeting that will return :
        # None if could not connect
        # True if already sent
        # False if not already sent, in this case we can proceed...
        alreadySent = self.ws4pmSettings.checkAlreadySentToPloneMeeting(self.context, (self.meetingConfigId,))
        if alreadySent:
            IStatusMessage(self.request).addStatusMessage(_(ALREADY_SENT_TO_PM_ERROR), "error")
            return self._redirectToRightPlace()
        elif alreadySent in (None, False):
            # None means that it was already sent but that it could not connect to PloneMeeting
            # False means that is was not sent, so no connection test is made to PloneMeeting for performance reason
            if alreadySent is False:
                # now connect to PloneMeeting
                client = self.ws4pmSettings._soap_connectToPloneMeeting()
            if alreadySent is None or not client:
                IStatusMessage(self.request).addStatusMessage(_(UNABLE_TO_CONNECT_ERROR), "error")
                return self._redirectToRightPlace()

        # do not go further if current user can not create an item in
        # PloneMeeting with any proposingGroup
        userInfos = self.ws4pmSettings._soap_getUserInfos(showGroups=True, suffix='creators')
        if not 'groups' in userInfos:
            userThatWillCreate = self.ws4pmSettings._getUserIdToUseInTheNameOfWith()
            IStatusMessage(self.request).addStatusMessage(_(NO_PROPOSING_GROUP_ERROR % userThatWillCreate), "error")
            return self._redirectToRightPlace()

        if 'form.button.Send' in self.request.form:
            # now that we can connect to the webservice, check that the user can actually trigger that action
            # indeed parameters are sent thru the request, and so someone could do nasty things...
            # check that the real currentUrl is on available in object_buttons actions for the user
            availableActions = self.portal.portal_actions.listFilteredActionsFor(self.context).get('object_buttons', [])
            # rebuild real url called by the action
            currentUrl = unicode(self.request['ACTUAL_URL'] + '?meetingConfigId=' + self.meetingConfigId, 'utf-8')
            # now check if this url is available in the actions for the user
            mayDoAction = False
            for action in availableActions:
                if action['url'] == currentUrl:
                    mayDoAction = True
                    break
            if not mayDoAction:
                raise Unauthorized

            # build the creationData
            creation_data = self._getCreationData(client)

            # call the SOAP method actually creating the item
            res = self.ws4pmSettings._soap_createItem(self.meetingConfigId,
                                                      self.proposingGroupId,
                                                      creation_data)
            if res:
                uid, warnings = res
                IStatusMessage(self.request).addStatusMessage(_(CORRECTLY_SENT_TO_PM_INFO),
                                                              "info")
                if warnings:
                    for warning in warnings[1]:
                        # show warnings in the web interface and add it to the Zope log
                        # do not show the DEFAULT_NO_WARNING_MESSAGE
                        if warning == DEFAULT_NO_WARNING_MESSAGE:
                            continue
                        else:
                            type = "warning"
                            logger.warning(warning)
                            IStatusMessage(self.request).addStatusMessage(_(warning), type)
                # finally save in the self.context annotation that the item has been sent
                annotations = IAnnotations(self.context)
                if not WS4PMCLIENT_ANNOTATION_KEY in annotations:
                    annotations[WS4PMCLIENT_ANNOTATION_KEY] = [self.meetingConfigId, ]
                else:
                    # do not use .append directly on the annotations or it does not save
                    # correctly and when Zope restarts, the added annotation is lost???
                    existingAnnotations = list(annotations[WS4PMCLIENT_ANNOTATION_KEY])
                    existingAnnotations.append(self.meetingConfigId)
                    annotations[WS4PMCLIENT_ANNOTATION_KEY] = existingAnnotations
            self._redirectToRightPlace()
        elif 'form.button.Cancel' in self.request.form:
            # case when not using the overlay popup
            self._redirectToRightPlace()
        else:
            return self.index()

    def _getCreationData(self, client):
        """
          Build creationData dict that will be used to actually create
          the item in PloneMeeting thru SOAP createItem call
        """
        data = self._buildDataDict()
        # now that every values are evaluated, build the CreationData
        creation_data = client.factory.create('CreationData')
        for elt in data:
            if not isinstance(data[elt], unicode):
                data[elt] = unicode(data[elt], 'utf-8')
            creation_data[elt] = data[elt]
        # initialize the externalIdentifier to the context UID
        creation_data['externalIdentifier'] = self.context.UID()
        return creation_data

    def _buildDataDict(self):
        """
        """
        data = OrderedDict()
        settings = self.ws4pmSettings.settings()
        for availableData in settings.field_mappings:
            field_name = availableData['field_name']
            expr = availableData['expression']
            # make the meetingConfigId available in the expression
            vars = {}
            vars['meetingConfigId'] = self.meetingConfigId
            vars['proposingGroupId'] = self.proposingGroupId
            # evaluate the expression
            try:
                data[field_name] = self.ws4pmSettings.renderTALExpression(self.context,
                                                                          self.portal,
                                                                          expr, vars)
            except Exception, e:
                IStatusMessage(self.request).addStatusMessage(
                    _(TAL_EVAL_FIELD_ERROR %
                      (settings.viewlet_display_condition, 'viewlet_display_condition', e)),
                    "error")
                return self.request.RESPONSE.redirect(self.context.absolute_url())
        return data

    def getDisplayableData(self):
        """
          Returns data to be displayed in the resume form
          Do not display :
          - externalIdentifier
          - empty values
        """
        data = self._buildDataDict()
        data.pop('externalIdentifier')
        for elt in data:
            if not data[elt].strip():
                data.pop(elt)
        return data

    def _redirectToRightPlace(self):
        """
          Depending on the fact that we are using a popup overlay or not,
          if not in a popup overlay redirect to context url so the message is displayed
        """
        if not 'ajax_load' in self.request:
            return self.request.RESPONSE.redirect(self.context.absolute_url())
        else:
            # tells the overlay popup that there are just messages to display
            self.request.set('show_send_to_pm_form', False)
            return self.index()

    def initProposingGroupId(self):
        """
          Initialize values for the 'proposingGroup' form field
        """
        res = []
        userInfos = self.ws4pmSettings._soap_getUserInfos(showGroups=True, suffix='creators')
        if not 'groups' in userInfos:
            return []
        res = []
        for group in userInfos['groups']:
            res.append((group['id'], group['title'],))
        return res


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
