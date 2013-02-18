import logging
logger = logging.getLogger('imio.pm.wsclient')

from AccessControl import Unauthorized
from zope.component import getMultiAdapter
from Products.Five import BrowserView
from Products.CMFCore.Expression import Expression, createExprContext
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _

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

    def __call__(self):
        """ """
        # first check that we can connect to the PloneMeeting webservices
        ws4pmSettings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        client = ws4pmSettings._soap_connectToPloneMeeting(addPortalMessage=False)
        if client is None:
            IStatusMessage(self.request).addStatusMessage(_(u"Unable to connect to PloneMeeting, check the 'WS4PM Client settings'!  Please contact system administrator!"), "warning")
            return self.request.RESPONSE.redirect(self.context.absolute_url())
        # now that we can connect to the webservice, check that the user can actually trigger that action
        # indeed paramters are sent thru the request, and so someone could do nasty things...
        # check that the real currentUrl is on available in object_buttons actions for the user
        availableActions = self.portal.portal_actions.listFilteredActionsFor(self.context)['object_buttons']
        # rebuild real url called by the action
        currentUrl = self.request['ACTUAL_URL'] + '?' + self.request['QUERY_STRING']
        # now check if this url is available in the actions for the user
        mayDoAction = False
        for action in availableActions:
            if action['url'] == currentUrl:
                mayDoAction = True
                break
        if not mayDoAction:
            raise Unauthorized

        # if we can connect and the user is allowed to trigger the action, proceed !
        settings = ws4pmSettings.settings()
        # check if not already sent to PloneMeeting...
        res = ws4pmSettings._soap_searchItems(**{'externalIdentifier': self.context.UID(),
                                                 'meetingConfigId': self.meetingConfigId})
        if res:
            IStatusMessage(self.request).addStatusMessage(_("This element has already been sent to PloneMeeting!"), "error")
            return self.request.RESPONSE.redirect(self.context.absolute_url())

        # build the creationData
        data = {}
        for availableData in settings.field_mappings:
            field_name = availableData['field_name']
            expression = availableData['expression'].strip()
            if expression.strip():
                ctx = createExprContext(self.context.aq_inner.aq_parent, self.portal, self.context)
                try:
                    res = Expression(expression)(ctx)
                    data[field_name] = res
                except Exception, e:
                    IStatusMessage(self.request).addStatusMessage(_(u"There was an error evaluating the TAL expression '%s' for the field '%s'!  " \
                                                                    "The error was : '%s'.  Please contact system administrator." % (expression, field_name, e)), "error")
                    return self.request.RESPONSE.redirect(self.context.absolute_url())

        # now that every values are evaluated, create the CreationData
        creationData = client.factory.create('CreationData')
        for elt in data:
            creationData[elt] = data[elt]
        # initialize the externalIdentifier to the context UID
        creationData['externalIdentifier'] = self.context.UID()
        # call the SOAP method actually creating the item
        res = ws4pmSettings._soap_createItem(self.meetingConfigId, self.proposingGroupId, creationData)
        if res:
            uid, warnings = res
            IStatusMessage(self.request).addStatusMessage(_(u"The item has been correctly sent to PloneMeeting."), "info")
            if warnings:
                for warning in warnings[1]:
                    # show warnings in the web interface for Managers and add it to the Zope log
                    if self.portal_state.member().has_role('Manager'):
                        IStatusMessage(self.request).addStatusMessage(_(warning), "warning")
                    logger.warning(warning)
        return self.request.RESPONSE.redirect(self.context.absolute_url())

