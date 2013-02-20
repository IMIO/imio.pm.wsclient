from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary


class pm_proposing_group_id_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every existing MeetingGroups in a distant PloneMeeting."""
        # query existing MeetingGroups from distant PM site if the default_pm_url is defined and working
        portal = getSite()
        # while called in an inline_validation, portal is not correct...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            portal = portal.aq_inner.aq_parent
        settings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        pmConfigInfos = settings._soap_getConfigInfos()
        terms = []
        if pmConfigInfos:
            for pmConfigInfo in pmConfigInfos:
                if not pmConfigInfo['type'] == 'MeetingGroup':
                    continue
                # force terms to be str or it may be 'suds.sax.text.Text' instances
                terms.append(SimpleTerm(str(pmConfigInfo['id']), str(pmConfigInfo['id']), str(pmConfigInfo['title']),))
            terms.append(SimpleTerm('GroupPM1', 'GroupPM1', 'GroupPM1'))
            terms.append(SimpleTerm('GroupPM2', 'GroupPM2', 'GroupPM2'))
            terms.append(SimpleTerm('GroupPM3', 'GroupPM3', 'GroupPM3'))
        return SimpleVocabulary(terms)
pm_proposing_group_id_vocabularyFactory = pm_proposing_group_id_vocabulary()


class pm_meeting_config_id_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every existing MeetingConfigs in a distant PloneMeeting."""
        # query existing MeetingGroups from distant PM site if the default_pm_url is defined and working
        portal = getSite()
        # while called in an inline_validation, portal is not correct...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            portal = portal.aq_inner.aq_parent
        settings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        pmConfigInfos = settings._soap_getConfigInfos()
        terms = []
        if pmConfigInfos:
            for pmConfigInfo in pmConfigInfos:
                if not pmConfigInfo['type'] == 'MeetingConfig':
                    continue
                terms.append(SimpleTerm(str(pmConfigInfo['id']), str(pmConfigInfo['id']), str(pmConfigInfo['title']),))
        return SimpleVocabulary(terms)
pm_meeting_config_id_vocabularyFactory = pm_meeting_config_id_vocabulary()


class possible_permissions_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every existing permissions."""
        terms = []
        portal = getSite()
        # while called in an inline_validation, portal is not correct...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            portal = portal.aq_inner.aq_parent
        for possible_permission in portal.acl_users.portal_role_manager.possible_permissions():
            terms.append(SimpleTerm(possible_permission, possible_permission, possible_permission))
        return SimpleVocabulary(terms)
possible_permissions_vocabularyFactory = possible_permissions_vocabulary()


class pm_item_data_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every available data we can use to create an item in the distant PloneMeeting."""
        terms = []

        # query existing item data from distant PM site if the default_pm_url is defined and working
        portal = getSite()
        # while called in an inline_validation, portal is not correct...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            portal = portal.aq_inner.aq_parent
        settings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        availableDatas = settings._soap_getItemCreationAvailableData()
        if availableDatas:
            for availableData in availableDatas:
                terms.append(SimpleTerm(str(availableData), str(availableData), str(availableData),))
        return SimpleVocabulary(terms)
pm_item_data_vocabularyFactory = pm_item_data_vocabulary()
