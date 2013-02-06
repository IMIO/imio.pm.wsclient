from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from zope.interface import implements

from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary


class pm_proposing_group_id_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []

        # query existing MeetingGroups from distant PM site if the default_pm_url is defined and working
        portal = getSite()
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        pmConfigInfos = ctrl._soap_getConfigInfos()
        if pmConfigInfos:
            terms.append(SimpleTerm('GroupPM1', 'GroupPM1', 'GroupPM1'))
            terms.append(SimpleTerm('GroupPM2', 'GroupPM2', 'GroupPM2'))
            terms.append(SimpleTerm('GroupPM3', 'GroupPM3', 'GroupPM3'))
        return SimpleVocabulary(terms)
pm_proposing_group_id_vocabularyFactory = pm_proposing_group_id_vocabulary()


class pm_meeting_config_id_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []

        # query existing MeetingGroups from distant PM site if the default_pm_url is defined and working
        portal = getSite()
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        pmConfigInfos = ctrl._soap_getConfigInfos()
        if pmConfigInfos:
            terms.append(SimpleTerm('meeting-config-college', 'MeetingConfigCollege', 'MeetingConfigCollege'))
            terms.append(SimpleTerm('meeting-config-council', 'MeetingConfigCouncil', 'MeetingConfigCouncil'))
        return SimpleVocabulary(terms)
pm_meeting_config_id_vocabularyFactory = pm_meeting_config_id_vocabulary()


class possible_permissions_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every existing permissions."""
        terms = []
        portal = getSite()
        for possible_permission in portal.acl_users.portal_role_manager.possible_permissions():
            terms.append(SimpleTerm(possible_permission, possible_permission, possible_permission))
        return SimpleVocabulary(terms)
possible_permissions_vocabularyFactory = possible_permissions_vocabulary()