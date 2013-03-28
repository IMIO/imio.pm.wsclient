from zope.component import getMultiAdapter
from zope.component.hooks import getSite
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from Products.statusmessages.interfaces import IStatusMessage
from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import TAL_EVAL_FIELD_ERROR


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
                terms.append(SimpleTerm(unicode(pmConfigInfo['id']),
                                        unicode(pmConfigInfo['id']),
                                        unicode(pmConfigInfo['title']),))
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
                terms.append(SimpleTerm(unicode(availableData),
                                        unicode(availableData),
                                        unicode(availableData),))
        return SimpleVocabulary(terms)
pm_item_data_vocabularyFactory = pm_item_data_vocabulary()


class proposing_groups_for_user_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every available proposingGroups for current user in a distant PloneMeeting."""
        portal = getSite()
        # while called in an inline_validation, portal is not correct...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            portal = portal.aq_inner.aq_parent
        ws4pmsettings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        field_mappings = ws4pmsettings.settings().field_mappings
        if not field_mappings:
            return SimpleVocabulary([])
        forcedProposingGroup = None
        vars = {}
        vars['meetingConfigId'] = portal.REQUEST.get('meetingConfigId')
        for field_mapping in field_mappings:
            # try to find out if a proposingGroup is forced in the configuration
            if field_mapping[u'field_name'] == 'proposingGroup':
                try:
                    forcedProposingGroup = ws4pmsettings.renderTALExpression(context,
                                                                             portal,
                                                                             field_mapping['expression'],
                                                                             vars)
                    break
                except Exception, e:
                    IStatusMessage(portal.REQUEST).addStatusMessage(
                        _(TAL_EVAL_FIELD_ERROR %
                          (field_mapping['expression'], field_mapping['field_name'], e)),
                        "error")
                    return SimpleVocabulary([])
        # even if we get a forcedProposingGroup, double check that the current user can actually use it
        userInfos = ws4pmsettings._soap_getUserInfos(showGroups=True, suffix='creators')
        if not userInfos or not 'groups' in userInfos:
            return SimpleVocabulary([])
        terms = []
        forcedProposingGroupExists = not forcedProposingGroup and True or False
        for group in userInfos['groups']:
            if forcedProposingGroup == group['id']:
                forcedProposingGroupExists = True
                terms.append(SimpleTerm(unicode(group['id']),
                                        unicode(group['id']),
                                        unicode(group['title']),))
                break
            if not forcedProposingGroup:
                terms.append(SimpleTerm(unicode(group['id']),
                                        unicode(group['id']),
                                        unicode(group['title']),))
        if not forcedProposingGroupExists:
            IStatusMessage(portal.REQUEST).addStatusMessage(
                _("The current user can not create an item with the proposingGroup forced "
                  "thru the configuration!  Please contact system administrator!"),
                "error")
            return
        return SimpleVocabulary(terms)
proposing_groups_for_user_vocabularyFactory = proposing_groups_for_user_vocabulary()


class categories_for_user_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every available categories for current user in a distant PloneMeeting."""
        portal = getSite()
        # while called in an inline_validation, portal is not correct...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            portal = portal.aq_inner.aq_parent
        ws4pmsettings = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        field_mappings = ws4pmsettings.settings().field_mappings
        if not field_mappings:
            return SimpleVocabulary([])
        forcedCategory = None
        vars = {}
        meetingConfigId = portal.REQUEST.get('meetingConfigId') or \
            portal.REQUEST.form.get('form.widgets.meetingConfigId')
        vars['meetingConfigId'] = meetingConfigId
        for field_mapping in field_mappings:
            # try to find out if a proposingGroup is forced in the configuration
            if field_mapping[u'field_name'] == 'category':
                try:
                    forcedCategory = ws4pmsettings.renderTALExpression(context,
                                                                       portal,
                                                                       field_mapping['expression'],
                                                                       vars)
                    break
                except Exception, e:
                    IStatusMessage(portal.REQUEST).addStatusMessage(
                        _(TAL_EVAL_FIELD_ERROR %
                          (field_mapping['expression'], field_mapping['field_name'], e)),
                        "error")
                    return SimpleVocabulary([])

        configInfos = ws4pmsettings._soap_getConfigInfos(showCategories=True)
        if not configInfos:
            return SimpleVocabulary([])
        categories = []
        # find categories for given meetingConfigId
        for configInfo in configInfos:
            if configInfo.id == meetingConfigId:
                categories = hasattr(configInfo, 'categories') and configInfo.categories or ()
                break
        # if not categories is returned, it means that the meetingConfig does
        # not use categories...
        if not categories:
            return SimpleVocabulary([])
        terms = []
        forcedCategoryExists = not forcedCategory and True or False
        for category in categories:
            if forcedCategory == category.id:
                forcedCategoryExists = True
                terms.append(SimpleTerm(unicode(category.id),
                                        unicode(category.id),
                                        unicode(category.title),))
                break
            if not forcedCategory:
                terms.append(SimpleTerm(unicode(category.id),
                                        unicode(category.id),
                                        unicode(category.title),))
        if not forcedCategoryExists:
            IStatusMessage(portal.REQUEST).addStatusMessage(
                _("The current user can not create an item with the category forced "
                  "thru the configuration!  Please contact system administrator!"),
                "error")
            return
        return SimpleVocabulary(terms)
categories_for_user_vocabularyFactory = categories_for_user_vocabulary()
