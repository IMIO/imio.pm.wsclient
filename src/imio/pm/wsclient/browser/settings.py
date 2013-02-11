from SOAPpy import Config, SOAPProxy, HTTPTransport, SOAPAddress
from SOAPpy.Types import faultType

from zope.component import getMultiAdapter, queryUtility
from zope.component.hooks import getSite

from zope.interface import Interface
from zope import schema

from z3c.form import button
from z3c.form import field

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.memoize.view import memoize

from plone.registry.interfaces import IRegistry 
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow

from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import SOAP_NAMESPACE


class IGeneratedActionsSchema(Interface):
    """Schema used for the datagrid field 'generated_actions' of IWS4PMClientSettings."""   
    condition = schema.TextLine(
        title=_("TAL Condition"),
        required=False
        )
    permissions = schema.Choice(
        title=_("Permissions"),
        required=False,
        vocabulary=u'imio.pm.wsclient.possible_permissions_vocabulary'
        )
    pm_proposing_group_id = schema.Choice(
        title=_("PloneMeeting proposing group id"),
        required=False,
        vocabulary=u'imio.pm.wsclient.pm_proposing_group_id_vocabulary'
        )
    pm_meeting_config_id = schema.Choice(
        title=_("PloneMeeting meetingConfig id"),
        required=False,
        vocabulary=u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')


class IWS4PMClientSettings(Interface):
    """
    Configuration of the WS4PM Client
    """
    pm_url = schema.TextLine(
        title=_(u"PloneMeeting URL"),
        description=_(u"Enter the PloneMeeting URL you want to work with."),
        required=True,
        )
    pm_username = schema.TextLine(
        title=_("PloneMeeting username to use"),
        required=True
        )
    pm_password = schema.Password(
        title=_("PloneMeeting password to use"),
        required=True
        )
    generated_actions = schema.List(
        title=_("Generated actions"),
        description=_("Enter a 'TAL condition' evaluated to show the action.  Choose permission(s) the user must have to see the action.  Enter a PloneMeeting proposingGroup id to force the creation of the item with this proposingGroup.  Warning, if the user can not create an item for this proposingGroup, a warning message will appear.  If left empty, if the user is in only one proposingGroup, it will be used automatically, if the user is in several proposingGroups, a popup will ask him which proposingGroup to use.  Finally, choose a meetingConfig the item will be created in."),
        value_type=DictRow(title=_("Actions"),
                           schema=IGeneratedActionsSchema,
                           required=False),
        required=False,
        )


class WS4PMClientSettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    schema = IWS4PMClientSettings
    label = _(u"WS4PM Client settings")
    description = _(u"""""")

    fields = field.Fields(IWS4PMClientSettings)
    fields['generated_actions'].widgetFactory = DataGridFieldFactory

    def updateFields(self):
        super(WS4PMClientSettingsEditForm, self).updateFields()
        portal = getSite()
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        # if we can not getConfigInfos from the given pm_url, we do not permit to edit other parameters
        generated_actions_field = self.fields.get('generated_actions')
        if not ctrl._soap_getConfigInfos():
            generated_actions_field.mode='display'
        else:
            if generated_actions_field.mode == 'display' and \
               not 'form.buttons.save' in self.request.form.keys():
                # only change mode while not in the "saving" process (that calls updateFields, but why?)
                # because it leads to loosing generated_actions because a [] is returned by extractDate here above
                self.fields.get('generated_actions').mode='input'
                #self.request.form.set('form.widgets.generated_actions')

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

    @memoize
    def _soap_connectToPloneMeeting(self):
        """Connect to distant PloneMeeting.
           Either return None or the connected client.
        """
        settings = self.settings()
        url = self.request.form.get('form.widgets.pm_url') or settings.pm_url
        username = self.request.form.get('form.widgets.pm_username') or settings.pm_username
        password = self.request.form.get('form.widgets.pm_password') or settings.pm_password
        AuthHTTPTransport.setAuthentication(username, password)
        client = None
        try:
            client = SOAPProxy(url, namespace=SOAP_NAMESPACE, transport=AuthHTTPTransport, )
            # client just contains data connections but don't really connect
            # call a SOAP server test method to check that everything is fine with given parameters
            client.testConnectionRequest('')
        except:
            IStatusMessage(self.request).addStatusMessage(_(u"Unable to connect with given url/username/password!"), "warning")
            return None
        return client

    @memoize
    def _soap_getConfigInfos(self):
        """Query the getConfigInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            try:
                return client.getConfigInfosRequest(dummy='')
            except faultType:
                pass


# Add special transport to be able to define authentication data
class AuthHTTPTransport(HTTPTransport):
    username = None
    passwd = None
    
    @classmethod
    def setAuthentication(cls,u,p):
        cls.username = u
        cls.passwd = p
          
    def call(self, addr, data, namespace, soapaction=None, encoding=None,
             http_proxy=None, config=Config, timeout=None):
        
        if not isinstance(addr, SOAPAddress):
            addr=SOAPAddress(addr, config)
            
        if self.username != None:
            addr.user = self.username+":"+self.passwd
            
        return HTTPTransport.call(self, addr, data, namespace, soapaction,
                                  encoding, http_proxy, config, timeout)
