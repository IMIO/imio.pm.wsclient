# -*- coding: utf-8 -*-

from dateutil import tz
from datetime import datetime
from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import CAN_NOT_SEE_LINKED_ITEMS_INFO
from imio.pm.wsclient.config import UNABLE_TO_CONNECT_ERROR
from imio.pm.wsclient.config import UNABLE_TO_DISPLAY_VIEWLET_ERROR
from imio.pm.wsclient.config import WS4PMCLIENT_ANNOTATION_KEY
from plone.app.layout.viewlets.common import ViewletBase
from plone.memoize.instance import memoize
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.schema.interfaces import IVocabularyFactory


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
            if not res:
                return False
        except Exception, e:
            return (_(UNABLE_TO_DISPLAY_VIEWLET_ERROR, mapping={'expr': settings.viewlet_display_condition,
                                                                'field_name': 'viewlet_display_condition',
                                                                'error': e}), 'error')
        # evaluate self.getPloneMeetingLinkedInfos
        linkedInfos = self.getPloneMeetingLinkedInfos()
        if isinstance(linkedInfos, tuple):
            # if self.getPloneMeetingLinkedInfos has errors, it returns
            # also a tuple with error message
            return linkedInfos
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

    @memoize
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
                },
            )
        except Exception, exc:
            return (_(u"An error occured while searching for linked items in PloneMeeting!  "
                      "The error message was : %s" % exc), 'error')
        # if we are here, it means that the current element is actually linked to item(s)
        # in PloneMeeting but the current user can not see it!
        if not items:
            # we return a message in a tuple
            return (_(CAN_NOT_SEE_LINKED_ITEMS_INFO), 'info')

        annotations = IAnnotations(self.context)
        sent_to = annotations[WS4PMCLIENT_ANNOTATION_KEY]
        res = []
        # to be able to know if some infos in PloneMeeting where not found
        # for current user, save the infos actually shown...
        settings = self.ws4pmSettings.settings()
        allowed_annexes_types = [line.values()[0] for line in settings.allowed_annexes_types]
        shownItemsMeetingConfigId = []
        for item in items:
            res.append(self.get_item_info(item))
            lastAddedItem = res[-1]
            shownItemsMeetingConfigId.append(lastAddedItem['extra_include_config']['id'])
            # XXX special case if something went wrong and there is an item in PM
            # that is not in the context sent_to annotation
            lastAddedItemMeetingConfigId = str(lastAddedItem['extra_include_config']['id'])
            if lastAddedItemMeetingConfigId not in sent_to:
                existingSentTo = list(sent_to)
                existingSentTo.append(lastAddedItemMeetingConfigId)
                annotations[WS4PMCLIENT_ANNOTATION_KEY] = existingSentTo
                sent_to = annotations[WS4PMCLIENT_ANNOTATION_KEY]
            if "extra_include_linked_items" in item and item["extra_include_linked_items"]:
                for linked_item in item["extra_include_linked_items"]:
                    res.append(self.get_item_info(linked_item))

        # if the number of items found is inferior to elements sent, it means
        # that some infos are not viewable by current user, we add special message
        if not len(items) == len(sent_to):
            # get meetingConfigs infos, use meetingConfig vocabulary
            factory = queryUtility(IVocabularyFactory, u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')
            meetingConfigVocab = factory(self.portal_state.portal())
            # add special result
            for sent in annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                if sent not in shownItemsMeetingConfigId:
                    # append a special result : nothing else but the meeting_config_id and title
                    # in extraInfos so sort here under works correctly
                    # in the linked viewlet template, we test if there is a 'UID' in the given infos, if not
                    # it means that it is this special message
                    res.append({'extra_include_config': {'id': sent,
                                                         'title': meetingConfigVocab.getTerm(sent).title}})

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
