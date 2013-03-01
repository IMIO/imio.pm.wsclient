from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
from suds.transport.http import HttpAuthenticated

from zope.annotation import IAnnotations

from zope.component import getMultiAdapter, queryUtility
from zope.component.hooks import getSite

from zope.interface import Interface, invariant, Invalid
from zope import schema

from zope.i18n import translate

from z3c.form import button
from z3c.form import field

from Products.CMFCore.Expression import Expression, createExprContext

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
from imio.pm.wsclient.config import ACTION_SUFFIX, WS4PMCLIENT_ANNOTATION_KEY


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
    viewlet_display_condition = schema.TextLine(
        title=_("Viewlet display condition"),
        description=_("Enter a TAL expression that will be evaluated to check if the viewlet displaying " \
                      "informations about the created items in PloneMeeting should be displayed.  " \
                      "If empty, the viewlet will only be displayed if an item is actually linked to it.  " \
                      "The element 'isLinked' representing this default behaviour is available in the TAL expression."),
        required=False
        )
    field_mappings = schema.List(
        title=_("Field accessor mappings"),
        description=_("For every available data you can send, define in the mapping a TAL expression that will be " \
                      "executed to obtain the correct value to send.  The 'meetingConfigId' and 'proposingGroupId' " \
                      "variables are also available for the expression."),
        value_type=DictRow(title=_("Actions"),
                           schema=IFieldMappingsSchema,
                           required=False),
        required=False
        )
    user_mappings = schema.Text(
        title=_("User ids mappings"),
        description=_("By default, while sending an element to PloneMeeting, the user id of the logged in user " \
                      "sending the element is considered and a check is made in PloneMeeting to see" \
                      "if the same user id also exists.  If it does not, you can define here the user mappings " \
                      "to use.  For example : 'jdoe' in current application correspond to 'johndoe' " \
                      "in PloneMeeting.  The format to use is <strong>one mapping by line with userIds separated by " \
                      "a '|'</strong>, for example : " \
                      "<br />currentAppUserId|plonemeetingCorrespondingUserId<br />anotherUserId|aUserIdInPloneMeeting"
                     ),
        required=False
        )
    generated_actions = schema.List(
        title=_("Generated actions"),
        description=_("Enter a 'TAL condition' evaluated to show the action.  " \
                      "Choose permission(s) the user must have to see the action.  " \
                      "Enter a PloneMeeting proposingGroup id to force the creation of the item with this " \
                      "proposingGroup.  Warning, if the user can not create an item for this proposingGroup, " \
                      "a warning message will appear.  If left empty, if the user is in only one proposingGroup, " \
                      "it will be used automatically, if the user is in several proposingGroups, a popup will ask " \
                      "him which proposingGroup to use.  Finally, choose a meetingConfig the item will be created in."),
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
                raise Invalid("User ids mapping : the format is not correct, it should be one mapping by line " \
                              "(no blank line!) with user ids separated by a '|', for example : " \
                              "currentAppUserId|plonemeetingCorrespondingUserId")


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
            generated_actions_field.mode = 'display'
            field_mappings.mode = 'display'
        else:
            if generated_actions_field.mode == 'display' and \
               not 'form.buttons.save' in self.request.form.keys():
                # only change mode while not in the "saving" process (that calls updateFields, but why?)
                # because it leads to loosing generated_actions because a [] is returned by extractDate here above
                self.fields.get('generated_actions').mode = 'input'
                self.fields.get('field_mappings').mode = 'input'

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

    @memoize
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
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        t = HttpAuthenticated(username=username, password=password)
        try:
            client = Client(url, doctor=d, transport=t)
            # call a SOAP server test method to check that everything is fine with given parameters
            client.service.testConnection('')
        except:
            # if we are really on the configuration panel, display relevant message
            if self.request.get('PATH_INFO', '').endswith('@@ws4pmclient-settings'):
                IStatusMessage(self.request).addStatusMessage(_(u"Unable to connect with given url/username/password!"),
                                                              "warning")
            return None
        return client

    def _soap_checkIsLinked(self, data):
        """Query the checkIsLinked SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.checkIsLinked(**data)

    @memoize
    def _soap_getConfigInfos(self):
        """Query the getConfigInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.getConfigInfos('')

    def _soap_searchItems(self, data):
        """Query the searchItems SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            # get the inTheNameOf userid if it was not already set
            if not 'inTheNameOf' in data:
                data['inTheNameOf'] = self._getUserIdToUseInTheNameOfWith()
            return client.service.searchItems(**data)

    def _soap_getItemInfos(self, data):
        """Query the getItemInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            # get the inTheNameOf userid if it was not already set
            if not 'inTheNameOf' in data:
                data['inTheNameOf'] = self._getUserIdToUseInTheNameOfWith()
            return client.service.getItemInfos(**data)

    @memoize
    def _soap_getItemCreationAvailableData(self):
        """Query SOAP WSDL to obtain the list of available fields useable while creating an item."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            # extract data from the CreationData ComplexType that is used to create an item
            namespace = str(client.wsdl.tns[1])
            return [str(data.name) for data in \
                    client.factory.wsdl.build_schema().types['CreationData', namespace].rawchildren[0].rawchildren]

    def _soap_createItem(self, meetingConfigId, proposingGroupId, creationData):
        """Query the createItem SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            try:
                # we create an item inTheNameOf the currently connected member
                # _getUserIdToCreateWith returns None if the settings defined username creates the item
                inTheNameOf = self._getUserIdToUseInTheNameOfWith()
                uid, warnings = client.service.createItem(meetingConfigId, proposingGroupId, creationData, inTheNameOf)
                return uid, warnings
            except Exception, exc:
                IStatusMessage(self.request).addStatusMessage(_(u"An error occured during the item creation in " \
                                                                "PloneMeeting!  The error message was : %s" % exc),
                                                              "error")

    def _getUserIdToUseInTheNameOfWith(self):
        """Returns the userId that will actually create the item.
           Returns None if we found out that it is the defined settings.pm_username
           that will create the item : either it is the currently connected user,
           or there is an existing user_mapping between currently connected user
           and settings.pm_username user."""
        member = self.context.portal_membership.getAuthenticatedMember()
        memberId = member.getId()
        # get username specified to connect to the SOAP distant site
        settings = self.settings()
        soapUsername = settings.pm_username and settings.pm_username.strip()
        # if current user is the user defined in the settings, return None
        if memberId == soapUsername:
            return None
        # check if a user_mapping exists
        if settings.user_mappings and settings.user_mappings.strip():
            for user_mapping in settings.user_mappings.split('\n'):
                localUserId, distantUserId = user_mapping.split('|')
                # if we found a mapping for the current user, check also
                # that the distantUserId to mapping is linking to is not the soapUsername
                if memberId == localUserId.strip():
                    if not soapUsername == distantUserId.strip():
                        return distantUserId.strip()
                    else:
                        return None
        return memberId

    def checkAlreadySentToPloneMeeting(self, context, meetingConfigIds=[]):
        """
          Check if the element as already been sent to PloneMeeting to avoid double sents
          If an item need to be doubled in PloneMeeting, it is PloneMeeting's duty
          If p_meetingConfigIds is empty (), then it checks every available meetingConfigId it was sent to...
          This script also wipe out every meetingConfigIds for wich the item does not exist anymore in PloneMeeting
        """
        annotations = IAnnotations(context)
        if WS4PMCLIENT_ANNOTATION_KEY in annotations:
            # the item seems to have been sent, but double check in case it was
            # deleted in PloneMeeting after having been sent
            # warning, here searchItems inTheNameOf the super user to be sure
            # that we can access it in PloneMeeting
            if not meetingConfigIds:
                # evaluate the meetingConfigIds in the annotation
                # this will wipe out the entire annotation
                meetingConfigIds = list(annotations[WS4PMCLIENT_ANNOTATION_KEY])
            for meetingConfigId in meetingConfigIds:
                res = self._soap_checkIsLinked({'externalIdentifier': context.UID(),
                                                'meetingConfigId': meetingConfigId, })
                if res:
                    return True
                else:
                    # either the item was deleted in PloneMeeting
                    # or it was never send, wipe out if it was deleted in PloneMeeting
                    if meetingConfigId in annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                        annotations[WS4PMCLIENT_ANNOTATION_KEY].remove(meetingConfigId)
                    if not annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                        # remove the entire annotation key if empty
                        del annotations[WS4PMCLIENT_ANNOTATION_KEY]
        return False

    def renderTALExpression(self, context, portal, expression, vars={}):
        """
          Renders given TAL expression in p_expression.
          p_vars contains extra variables that will be done available in the TAL expression to render
        """
        res = ''
        if expression:
            expression = expression.strip()
            ctx = createExprContext(context.aq_inner.aq_parent, portal, context)
            ctx.vars.update(vars)
            res = Expression(expression)(ctx)
        # make sure we do not return None because it breaks SOAP call
        return res or u''


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
            for actToGen in event.record.value:
                actionId = "%s%d" % (ACTION_SUFFIX, i)
                action = Action(actionId,
                                title=translate('Send to',
                                                domain='imio.pm.wsclient',
                                                mapping={'meetingConfigTitle': actToGen['pm_meeting_config_id']},
                                                context=portal.REQUEST),
                           description='', i18n_domain='imio.pm.wsclient',
                           url_expr='string:${object_url}/@@send_to_plonemeeting?meetingConfigId=%s&proposingGroupId=%s'
                                    % (actToGen['pm_meeting_config_id'],
                                       actToGen['pm_proposing_group_id']),
                           icon_expr='',
                           available_expr=actToGen['condition'],
                           permissions=(actToGen['permissions'], ),
                           visible=True)
                object_buttons._setObject(actionId, action)
                i = i + 1
