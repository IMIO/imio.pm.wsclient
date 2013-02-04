from zope.component import getUtility
from zope.interface import Interface, implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope import schema

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.registry.interfaces import IRegistry 
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow

from plone.autoform.directives import widget

from imio.pm.wsclient import WS4PMClientMessageFactory as _


class pm_group_id_vocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        # query existing MeetingGroups from distant PM site if the default_pm_url is defined and working
        import urllib2
        from suds.client import Client
        from suds.xsd.doctor import ImportDoctor, Import
        from suds.transport.http import HttpAuthenticated
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IWS4PMClientSettings)
        # get the defined plonemeeting_wsdl_url
        url = settings.plonemeeting_wsdl_url
        t = HttpAuthenticated(username='secretaire', password='meeting')
        if not url:
            terms.append(SimpleTerm('Enter a valid value in for the PloneMeeting WSDL URL and save this form', 'Enter a valid value in for the PloneMeeting WSDL URL and save this form', 'Enter a valid value in for the PloneMeeting WSDL URL and save this form'))
        else:
            try:
                client = Client(url, doctor=d, transport=t)
            except urllib2.URLError:
                terms.append(SimpleTerm('Enter a valid value in for the PloneMeeting WSDL URL and save this form', 'Enter a valid value in for the PloneMeeting WSDL URL and save this form', 'Enter a valid value in for the PloneMeeting WSDL URL and save this form'))
        return SimpleVocabulary(terms)
        
pm_group_id_vocabularyFactory = pm_group_id_vocabulary()


class IGroupsMappingSchema(Interface):
    local_group_id = schema.Choice(title=_("Local group id"), required=False, vocabulary=u'plone.app.vocabularies.Groups')
    pm_group_id = schema.Choice(title=_("PloneMeeting group id"), required=False, vocabulary=u'imio.pm.wsclient.pm_group_id_vocabulary')


class IWS4PMClientSettings(Interface):
    """
    Configuration of the WS4PM Client
    """
    plonemeeting_wsdl_url = schema.TextLine(
        title=_(u"PloneMeeting WSDL URL"),
        description=_(u"Enter the PloneMeeting WSDL URL you want to work with."),
        required=False,
        )
    groups_mappings = schema.List(
        title=_("Local groups to PloneMeeting groups mappings"),
        value_type=DictRow(title=_("Mapping"),
                           schema=IGroupsMappingSchema,
                           required=False),
        required=False,
        )
    widget(groups_mappings=DataGridFieldFactory)


class WS4PMClientSettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    schema = IWS4PMClientSettings
    label = _(u"WS4PM Client settings")
    description = _(u"""""")

    def updateFields(self):
        super(WS4PMClientSettingsEditForm, self).updateFields()

    def updateWidgets(self):
        super(WS4PMClientSettingsEditForm, self).updateWidgets()


class WS4PMClientSettings(ControlPanelFormWrapper):
    form = WS4PMClientSettingsEditForm
    index = ViewPageTemplateFile('settings.pt')


