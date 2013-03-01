from zope.component import getMultiAdapter

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.memoize.instance import memoize
from plone.app.layout.viewlets.common import ViewletBase

from imio.pm.wsclient import WS4PMClientMessageFactory as _


class PloneMeetingInfosViewlet(ViewletBase):
    """This viewlet display informations from PloneMeeting if the current object has been 'sent' to it.
       This viewlet will be displayed only if there are informations to show."""

    index = ViewPageTemplateFile('templates/plonemeeting_infos.pt')

    def update(self):
        self.portal_state = getMultiAdapter((self.context, self.request),
                                            name=u'plone_portal_state')
        self.ws4pmSettings = getMultiAdapter((self.portal_state.portal(), self.request), name='ws4pmclient-settings')

    @memoize
    def available(self):
        """
          Check if the viewlet is available and needs to be shown.
          This method returns either True or False, or a tuple of str
          that contains an information message (str1 is the translated message
          and str2 is the message type : info, error, warning).
        """
        # if we have an annotation specifying that the item was sent, we show the viewlet
        settings = self.ws4pmSettings.settings()
        isLinked = self.ws4pmSettings.checkAlreadySentToPloneMeeting(self.context)
        # in case it could not connect to PloneMeeting, checkAlreadySentToPloneMeeting returns None
        if isLinked == None:
            return (_(u"Unable to connect to PloneMeeting, check the 'WS4PM Client settings'! "\
                   "Please contact system administrator!"), "error")
        viewlet_display_condition = settings.viewlet_display_condition
        # if we have no defined viewlet_display_condition, use the isLinked value
        if not viewlet_display_condition or not viewlet_display_condition.strip():
            return isLinked
        # add 'isLinked' to data available in the TAL expression
        vars = {}
        vars['isLinked'] = isLinked
        try:
            res = self.ws4pmSettings.renderTALExpression(self.context,
                                                         self.portal_state.portal(),
                                                         settings.viewlet_display_condition,
                                                         vars)
        except Exception, e:
            return (_(u"Unable to display informations about the potentially linked item in PloneMeeting because " \
                   "there was an error evaluating the TAL expression '%s' for the field '%s'!  " \
                   "The error was : '%s'.  Please contact system administrator." % (settings.viewlet_display_condition,
                                                                                    'viewlet_display_condition', e)),
                    'error')
        return bool(res)

    @memoize
    def getPloneMeetingLinkedInfos(self):
        """Search items created for context.
           To get every informations we need, we will use getItemInfos(showExtraInfos=True)
           because we need the meetingConfig id and title...
           So search the items with searchItems then query again each found items
           with getConfigInfos."""
        items = self.ws4pmSettings._soap_searchItems({'externalIdentifier': self.context.UID()})
        if not items:
            return {}
        res = []
        for item in items:
            res.append(self.ws4pmSettings._soap_getItemInfos({'UID': item['UID'], 'showExtraInfos': True})[0])
        return res

    def displayMeetingDate(self, meeting_date):
        """Display a correct related meeting date :
           - if linked to a meeting, either '-'
           - manage displayed hours (hide hours if 00:00)"""
        if meeting_date.year == 1950:
            return '-'
        long_format = True
        if meeting_date.hour == 0 and meeting_date.minute == 0:
            long_format = False
        return self.context.restrictedTraverse('@@plone').toLocalizedTime(meeting_date, long_format=long_format)
