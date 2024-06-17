# -*- coding: utf-8 -*-

from dateutil import tz
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
        except Exception as e:
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

    @memoize
    def getPloneMeetingLinkedInfos(self):
        """Search items created for context.
           To get every informations we need, we will use getItemInfos(showExtraInfos=True)
           because we need the meetingConfig id and title...
           So search the items with searchItems then query again each found items
           with getConfigInfos.
           If we encounter an error, we return a tuple as 'usual' like in self.available"""
        try:
            items = self.ws4pmSettings._soap_searchItems({'externalIdentifier': self.context.UID()})
        except Exception as exc:
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
        allowed_annexes_types = [list(line.values())[0] for line in settings.allowed_annexes_types]
        shownItemsMeetingConfigId = []
        for item in items:
            res.append(self.ws4pmSettings._soap_getItemInfos({'UID': item['UID'],
                                                              'showExtraInfos': True,
                                                              'showAnnexes': True,
                                                              'allowed_annexes_types': allowed_annexes_types,
                                                              'include_annex_binary': False,
                                                              'showExtraInfos': True,
                                                              'showTemplates': True})[0])
            lastAddedItem = res[-1]
            shownItemsMeetingConfigId.append(lastAddedItem['extraInfos']['meeting_config_id'])
            # XXX special case if something went wrong and there is an item in PM
            # that is not in the context sent_to annotation
            lastAddedItemMeetingConfigId = str(lastAddedItem['extraInfos']['meeting_config_id'])
            if lastAddedItemMeetingConfigId not in sent_to:
                existingSentTo = list(sent_to)
                existingSentTo.append(lastAddedItemMeetingConfigId)
                annotations[WS4PMCLIENT_ANNOTATION_KEY] = existingSentTo
                sent_to = annotations[WS4PMCLIENT_ANNOTATION_KEY]

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
                    res.append({'extraInfos': {'meeting_config_id': sent,
                                               'meeting_config_title': meetingConfigVocab.getTerm(sent).title}})

        # sort res to comply with sent order, for example sent first to college then council
        def sortByMeetingConfigId(x, y):
            return cmp(sent_to.index(x['extraInfos']['meeting_config_id']),
                       sent_to.index(y['extraInfos']['meeting_config_id']))
        res.sort(sortByMeetingConfigId)
        return res

    def displayMeetingDate(self, meeting_date):
        """Display a correct related meeting date :
           - if linked to a meeting, either '-'
           - manage displayed hours (hide hours if 00:00)"""
        if meeting_date.year == 1950:
            return '-'

        # now determinate result of toLocalizedTime before calling it...
        # we will just check if given p_meeting_date that is UTC would have
        # his hour to 0 after being localized to relevant timezone (what toLocalizedTime does)
        # localize meetingDate because it does not work with naive dates
        localMeetingDate = meeting_date.replace(tzinfo=tz.tzlocal())
        delta = localMeetingDate.utcoffset()
        utcMeetingDate = localMeetingDate - delta
        # set utcMeetingDate as being UTC
        utcMeetingDate = utcMeetingDate.replace(tzinfo=tz.tzutc())
        # if hour is 0, hide it, so call toLocalizedTime with long_format=False
        if utcMeetingDate.astimezone(tz.tzlocal()).hour == 0:
            long_format = False
        else:
            long_format = True
        return self.context.restrictedTraverse('@@plone').toLocalizedTime(meeting_date, long_format=long_format)
