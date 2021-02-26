from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class pm_meeting_config_id_vocabulary(object):
    """
      Overrides the existing imio.pm.wsclient.browser.vocabularies.pm_meeting_config_id_vocabulary
      vocabulary that needs PloneMeeting to work and in the testSettings.py we do not have PloneMeeting...
      For other tests, the existing vocabulary is used.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        """Query every existing MeetingConfigs in a distant PloneMeeting."""
        # query existing MeetingGroups from distant PM site if the default_pm_url is defined and working
        terms = []
        terms.append(SimpleTerm(u'plonegov-assembly', u'plonegov-assembly', u'PloneGov Assembly', ))
        terms.append(SimpleTerm(u'plonemeeting-assembly', u'plonemeeting-assembly', u'PloneMeeting Assembly', ))
        return SimpleVocabulary(terms)


pm_meeting_config_id_vocabularyFactory = pm_meeting_config_id_vocabulary()
