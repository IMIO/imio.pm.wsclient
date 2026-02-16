# -*- coding: utf-8 -*-

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import CAN_NOT_SEE_LINKED_ITEMS_INFO
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import UNABLE_TO_DISPLAY_VIEWLET_ERROR
from plone.app.layout.viewlets.common import ViewletBase
from plone.memoize.instance import memoize
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter


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
        if isLinked is None:
            return (_(UNABLE_TO_CONNECT_ERROR), 'error')
        viewlet_display_condition = settings.viewlet_display_condition
        # if we have no defined viewlet_display_condition, use the isLinked value
        # if not viewlet_display_condition or not viewlet_display_condition.strip():
        #     return isLinked
        if viewlet_display_condition and viewlet_display_condition.strip():
            # add 'isLinked' to data available in the TAL expression
            vars = {}
            vars['isLinked'] = isLinked
            try:
                res = self.ws4pmSettings.renderTALExpression(self.context,
                                                             self.portal_state.portal(),
                                                             settings.viewlet_display_condition,
                                                             vars)
                if not res:
                    return False
            except Exception as e:
                return (_(UNABLE_TO_DISPLAY_VIEWLET_ERROR, mapping={'expr': settings.viewlet_display_condition,
                                                                    'field_name': 'viewlet_display_condition',
                                                                    'error': e}), 'error')
        # evaluate self.getPloneMeetingLinkedInfos
        self.linkedInfos = self.getPloneMeetingLinkedInfos()
        if isinstance(self.linkedInfos, tuple):
            # if self.getPloneMeetingLinkedInfos has errors, it returns
            # also a tuple with error message
            return self.linkedInfos
        return True

    def get_item_info(self, item):
        return self.ws4pmSettings._rest_getItemInfos(
            {
                'UID': item['UID'],
                'extra_include': 'meeting,pod_templates,annexes,config',
                'extra_include_meeting_additional_values': '*',
                'metadata_fields': 'review_state,creators,category,preferredMeeting',
                'fullobjects': None,
            }
        )[0]

    # @memoize
    def getPloneMeetingLinkedInfos(self):
        """Search items created for context.
           To get every informations we need, we will use getItemInfos(showExtraInfos=True)
           because we need the meetingConfig id and title...
           So search the items with searchItems then query again each found items
           with getConfigInfos.
           If we encounter an error, we return a tuple as 'usual' like in self.available"""
        try:
            items = self.ws4pmSettings._rest_searchItems(
                {
                    'externalIdentifier': self.context.UID(),
                    'extra_include': 'linked_items',
                    'extra_include_linked_items_mode': 'every_successors',
                    'metadata_fields': 'review_state,creators,category,preferredMeeting',
                    'type': None,  # We need to pass None because we need to search across every type of MeetingItem
                    # This is made to handle a special case where there is no user "inNameOf" so the PM side can't
                    # get all the MeetingItems types based on the inNameOf user.
                },
            )
        except Exception as exc:
            return (_(u"An error occured while searching for linked items in PloneMeeting!  "
                      "The error message was : %s" % exc), 'error')
        # if we are here, it means that the current element is actually linked to item(s)
        # in PloneMeeting but the current user can not see it!
        if not items:
            # we return a message in a tuple
            return (_(CAN_NOT_SEE_LINKED_ITEMS_INFO), 'info')

        res = []
        # to be able to know if some infos in PloneMeeting where not found
        # for current user, save the infos actually shown...
        for item in items:
            res.append(self.get_item_info(item))
            if "extra_include_linked_items" in item and item["extra_include_linked_items"]:
                for linked_item in item["extra_include_linked_items"]:
                    res.append(self.get_item_info(linked_item))

        # sort res to comply with sent order, for example sent first to college then council
        def sortByMeetingConfigId(x, y):
            return cmp(x["created"], y["created"])
        res.sort(sortByMeetingConfigId, reverse=True)
        return res

    def displayMeetingDate(self, meeting_date):
        """Display a correct related meeting date :
           - if linked to a meeting, either '-'
        """
        if not meeting_date:
            return '-'
        return meeting_date
