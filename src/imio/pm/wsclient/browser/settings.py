from zope.component import getMultiAdapter, queryUtility
from zope.component.hooks import getSite

from zope.interface import Interface
from zope import schema

from z3c.form import button

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.registry.interfaces import IRegistry 
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow

from plone.autoform.directives import widget

from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _


class IGeneratedActionsSchema(Interface):
    
    condition = schema.TextLine(title=_("TAL Condition"), required=False)
    permissions = schema.Choice(title=_("Permissions"), required=False, vocabulary=u'imio.pm.wsclient.possible_permissions_vocabulary')
    pm_proposing_group_id = schema.Choice(title=_("PloneMeeting proposing group id"), required=False, vocabulary=u'imio.pm.wsclient.pm_proposing_group_id_vocabulary')
    pm_meeting_config_id = schema.Choice(title=_("PloneMeeting meetingConfig id"), required=False, vocabulary=u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')
    pm_username = schema.TextLine(title=_("PloneMeeting username to use"), required=False)
    pm_password = schema.TextLine(title=_("PloneMeeting password to use"), required=False)

class IWS4PMClientSettings(Interface):
    """
    Configuration of the WS4PM Client
    """
    plonemeeting_wsdl_url = schema.TextLine(
        title=_(u"PloneMeeting WSDL URL"),
        description=_(u"Enter the PloneMeeting WSDL URL you want to work with."),
        required=False,
        )
    generated_actions = schema.List(
        title=_("Generated actions"),
        value_type=DictRow(title=_("Actions"),
                           schema=IGeneratedActionsSchema,
                           required=False),
        required=False,
        )

    widget(generated_actions=DataGridFieldFactory)


class WS4PMClientSettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    schema = IWS4PMClientSettings
    label = _(u"WS4PM Client settings")
    description = _(u"""""")

    def updateFields(self):
        super(WS4PMClientSettingsEditForm, self).updateFields()
        portal = getSite()
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        # if we can not connect to the given plonemeeting_wsdl_url, we do not permit to edit other parameters
        if not ctrl._soap_connectToPloneMeeting():
            self.fields.get('generated_actions').mode='display'

    def updateWidgets(self):
        super(WS4PMClientSettingsEditForm, self).updateWidgets()

    @button.buttonAndHandler(_('Save'), name=None)
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)
        IStatusMessage(self.request).addStatusMessage(_(u"Changes saved"),
                                                      "info")
        self.context.REQUEST.RESPONSE.redirect("@@ws4pmclient-settings")

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_(u"Edit cancelled"),
                                                      "info")
        self.request.response.redirect("%s/%s" % (self.context.absolute_url(),
                                                  self.control_panel_view))


class WS4PMClientSettings(ControlPanelFormWrapper):
    form = WS4PMClientSettingsEditForm
    index = ViewPageTemplateFile('settings.pt')

    def settings(self):
        """ """
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IWS4PMClientSettings, check=False)
        return settings

    def _soap_connectToPloneMeeting(self):
        """Connect to distant PloneMeeting.
           Either return None or the connected client.
        """
        from suds.client import Client
        from suds.xsd.doctor import ImportDoctor, Import
        from suds.transport.http import HttpAuthenticated
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        settings = self.settings()
        # get the defined plonemeeting_wsdl_url
        url = settings.plonemeeting_wsdl_url
        # build the authentication envelope
        t = HttpAuthenticated(username='secretaire', password='meeting')
        try:
            client = Client(url, doctor=d, transport=t)
            return client
        except Exception, e:
            IStatusMessage(self.request).addStatusMessage(_(u"Unable to connect using given WSDL URL, the error was : %s" % str(e)),
                                                      "warning")
            return None

    def _soap_getConfigInfos(self):
        """Query the getConfigInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        return bool(client)