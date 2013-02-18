from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
from suds.transport.http import HttpAuthenticated

from zope.component import getMultiAdapter, queryUtility
from zope.component.hooks import getSite

from zope.interface import Interface, invariant, Invalid
from zope import schema

from zope.i18n import translate

from z3c.form import button
from z3c.form import field

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.memoize.view import memoize

from plone.registry.interfaces import IRegistry, IRecordModifiedEvent

from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow

from Products.CMFCore.ActionInformation import Action
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import ACTION_SUFFIX


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

class IFieldMappingsSchema(Interface):
    """Schema used for the datagrid field 'field_mappings' of IWS4PMClientSettings."""   
    field_name = schema.Choice(
        title=_("PloneMeeting field name"),
        required=False,
        vocabulary=u'imio.pm.wsclient.pm_item_data_vocabulary'
        )
    expression = schema.TextLine(
        title=_("TAL expression to evaluate to get the value to use for the given data"),
        required=False,
        )


class IWS4PMClientSettings(Interface):
    """
    Configuration of the WS4PM Client
    """
    pm_url = schema.TextLine(
        title=_(u"PloneMeeting WSDL URL"),
        description=_(u"Enter the PloneMeeting WSDL URL you want to work with."),
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
    field_mappings = schema.List(
        title=_("Field accessor mappings"),
        description=_("For every available data you can send, define in the mapping a TAL expression that will be executed to obtain the correct value to send"),
        value_type=DictRow(title=_("Actions"),
                           schema=IFieldMappingsSchema,
                           required=False),
        required=False
        )
    user_mappings = schema.Text(
        title=_("User ids mappings"),
        description=_("By default, while sending an element to PloneMeeting, the user id of the logged in user sending the element is considered and a check is made in PloneMeeting to see" \
                      "if the same user id also exists.  If it does not, you can define here the user mappings to use.  For example : 'jdoe' in current application correspond to 'johndoe' " \
                      "in PloneMeeting.  The format to use is <strong>one mapping by line with userIds separated by a '|'</strong>, for example : <br />currentAppUserId|plonemeetingCorrespondingUserId<br />anotherUserId|aUserIdInPloneMeeting"),
        required=False
        )
    generated_actions = schema.List(
        title=_("Generated actions"),
        description=_("Enter a 'TAL condition' evaluated to show the action.  Choose permission(s) the user must have to see the action.  Enter a PloneMeeting proposingGroup id to force the creation of the item with this proposingGroup.  Warning, if the user can not create an item for this proposingGroup, a warning message will appear.  If left empty, if the user is in only one proposingGroup, it will be used automatically, if the user is in several proposingGroups, a popup will ask him which proposingGroup to use.  Finally, choose a meetingConfig the item will be created in."),
        value_type=DictRow(title=_("Actions"),
                           schema=IGeneratedActionsSchema,
                           required=False),
        required=False,
        )

    @invariant
    def isUserMappingsCorrectFormat(settings):
        user_mappings = settings.user_mappings
        for user_mapping in user_mappings.split('\n'):
            try:
                localuser, pmuser = user_mapping.split('|')
            except:
                raise Invalid("User ids mapping : the format is not correct, it should be one mapping by line (no blank line!) with user ids separated by a '|', for example : currentAppUserId|plonemeetingCorrespondingUserId")


class WS4PMClientSettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    schema = IWS4PMClientSettings
    label = _(u"WS4PM Client settings")
    description = _(u"""""")

    fields = field.Fields(IWS4PMClientSettings)
    fields['generated_actions'].widgetFactory = DataGridFieldFactory
    fields['field_mappings'].widgetFactory = DataGridFieldFactory

    def updateFields(self):
        super(WS4PMClientSettingsEditForm, self).updateFields()
        portal = getSite()
        # this is also called by the kss inline_validation, avoid too much work...
        if not portal.__module__ == 'Products.CMFPlone.Portal':
            return
        ctrl = getMultiAdapter((portal, portal.REQUEST), name='ws4pmclient-settings')
        # if we can not getConfigInfos from the given pm_url, we do not permit to edit other parameters
        generated_actions_field = self.fields.get('generated_actions')
        field_mappings = self.fields.get('field_mappings')
        if not ctrl._soap_getConfigInfos():
            generated_actions_field.mode='display'
            field_mappings.mode='display'
        else:
            if generated_actions_field.mode == 'display' and \
               not 'form.buttons.save' in self.request.form.keys():
                # only change mode while not in the "saving" process (that calls updateFields, but why?)
                # because it leads to loosing generated_actions because a [] is returned by extractDate here above
                self.fields.get('generated_actions').mode='input'
                self.fields.get('field_mappings').mode='input'

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
    def _soap_connectToPloneMeeting(self, addPortalMessage=True):
        """Connect to distant PloneMeeting.
           Either return None or the connected client.
           If given p_addPortalMessage is True, portal_messages will be added if necessary.
           This is useful if we want to call this method and add another portal_message than the one added here under.
        """
        settings = self.settings()
        url = self.request.form.get('form.widgets.pm_url') or settings.pm_url
        username = self.request.form.get('form.widgets.pm_username') or settings.pm_username
        password = self.request.form.get('form.widgets.pm_password') or settings.pm_password
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        t = HttpAuthenticated(username=username, password=password)
        try:
            client = Client(url, doctor=d, transport=t)
            # call a SOAP server test method to check that everything is fine with given parameters
            client.service.testConnection()
        except:
            if addPortalMessage:
                IStatusMessage(self.request).addStatusMessage(_(u"Unable to connect with given url/username/password!"), "warning")
            return None
        return client

    @memoize
    def _soap_getConfigInfos(self):
        """Query the getConfigInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.getConfigInfos()

    def _soap_searchItems(self, **data):
        """Query the searchItems SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.searchItems(**data)

    def _soap_getItemInfos(self, **data):
        """Query the getItemInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.getItemInfos(**data)

    @memoize
    def _soap_getItemCreationAvailableData(self):
        """Query SOAP WSDL to obtain the list of available fields useable while creating an item."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            # extract data from the CreationData ComplexType that is used to create an item
            namespace = str(client.wsdl.tns[1])
            return [data.name for data in client.factory.wsdl.build_schema().types['CreationData', namespace].rawchildren[0].rawchildren]

    @memoize
    def _soap_createItem(self, meetingConfigId, proposingGroupId, creationData):
        """Query the createItem SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            try:
                uid, warnings = client.service.createItem(meetingConfigId, proposingGroupId, creationData=creationData)
                return uid, warnings
            except Exception, exc:
                IStatusMessage(self.request).addStatusMessage(_(u"An error occured during the item creation in PloneMeeting!  The error message was : %s" % exc), "error")


def notify_configuration_changed(event):
    """Event subscriber that is called every time the configuration changed."""
    portal = getSite()

    if IRecordModifiedEvent.providedBy(event):
        # generated_actions changed, we need to update generated actions in portal_actions
        if event.record.fieldName == 'generated_actions':
            # if generated_actions have been changed, remove every existing generated_actions then recreate them
            # first remove every actions starting with ACTION_SUFFIX
            object_buttons = portal.portal_actions.object_buttons
            for object_button in object_buttons.objectValues():
                if object_button.id.startswith(ACTION_SUFFIX):
                    object_buttons.manage_delObjects([object_button.id])
            # then recreate them
            i = 1
            for actionToGenerate in event.record.value:
                actionId = "%s%d" % (ACTION_SUFFIX, i)
                action = Action(actionId, title=translate('Send to', domain='imio.pm.wsclient',
                                                          mapping={'meetingConfigTitle': actionToGenerate['pm_meeting_config_id']},
                                                          context=portal.REQUEST),
                           description='', i18n_domain='imio.pm.wsclient',
                           url_expr='string:${object_url}/@@send_to_plonemeeting?meetingConfigId=%s&proposingGroupId=%s' % \
                                    (actionToGenerate['pm_meeting_config_id'], actionToGenerate['pm_proposing_group_id']),
                           icon_expr='', available_expr=actionToGenerate['condition'], permissions=('View',), visible=True)
                object_buttons._setObject(actionId, action)
                i = i + 1

