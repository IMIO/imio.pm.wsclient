from AccessControl import Unauthorized
from zope.component import getMultiAdapter
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _

class SendToPloneMeetingView(BrowserView):
    """
      This manage the action that sends the element to PloneMeeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def __call__(self):
        """ """
        # first check that we can connect to the PloneMeeting webservices
        settings = getMultiAdapter((self.portal, self.request), name='ws4pmclient-settings')
        client = settings._soap_connectToPloneMeeting(addPortalMessage=False)
        if client is None:
            IStatusMessage(self.request).addStatusMessage(_(u"Unable to connect to PloneMeeting, check the 'WS4PM Client settings'!"), "warning")
            return self.request.RESPONSE.redirect(self.context.absolute_url())
        # now that we can connect to the webservice, check that the user can actually trigger that action
        # indeed paramters are sent thru the request, and so someone could do nasty things...
        # check that the real currentUrl is on available in object_buttons actions for the user
        availableActions = self.portal.portal_actions.listFilteredActionsFor(self.context)['object_buttons']
        # build real url called by the action
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
