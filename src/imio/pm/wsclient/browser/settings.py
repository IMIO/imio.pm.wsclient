from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
from suds.transport.http import HttpAuthenticated

from zope.annotation import IAnnotations

from zope.component import getMultiAdapter, queryUtility
from zope.component.hooks import getSite

from zope.interface import Interface
from zope import schema
from zope.schema.interfaces import IVocabularyFactory

from zope.i18n import translate

from z3c.form import button
from z3c.form import field

from Products.CMFCore.Expression import Expression, createExprContext

from plone.memoize.view import memoize

from plone.registry.interfaces import IRegistry, IRecordModifiedEvent

from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow

from Products.CMFCore.ActionInformation import Action
from Products.statusmessages.interfaces import IStatusMessage

from imio.pm.wsclient import WS4PMClientMessageFactory as _
from imio.pm.wsclient.config import ACTION_SUFFIX, WS4PMCLIENT_ANNOTATION_KEY, \
    CONFIG_UNABLE_TO_CONNECT_ERROR, CONFIG_CREATE_ITEM_PM_ERROR


class IGeneratedActionsSchema(Interface):
    """Schema used for the datagrid field 'generated_actions' of IWS4PMClientSettings."""
    condition = schema.TextLine(
        title=_("TAL Condition"),
        required=False,)
    permissions = schema.Choice(
        title=_("Permissions"),
        required=False,
        vocabulary=u'imio.pm.wsclient.possible_permissions_vocabulary')
    pm_meeting_config_id = schema.Choice(
        title=_("PloneMeeting meetingConfig id"),
        required=True,
        vocabulary=u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')


class IFieldMappingsSchema(Interface):
    """Schema used for the datagrid field 'field_mappings' of IWS4PMClientSettings."""
    field_name = schema.Choice(
        title=_("PloneMeeting field name"),
        required=True,
        vocabulary=u'imio.pm.wsclient.pm_item_data_vocabulary')
    expression = schema.TextLine(
        title=_("TAL expression to evaluate for the corresponding PloneMeeting field name"),
        required=True,)


class IUserMappingsSchema(Interface):
    """Schema used for the datagrid field 'user_mappings' of IWS4PMClientSettings."""
    local_userid = schema.TextLine(
        title=_("Local user id"),
        required=True)
    pm_userid = schema.TextLine(
        title=_("PloneMeeting corresponding user id"),
        required=True,)


class IWS4PMClientSettings(Interface):
    """
    Configuration of the WS4PM Client
    """
    pm_url = schema.TextLine(
        title=_(u"PloneMeeting WSDL URL"),
        description=_(u"Enter the PloneMeeting WSDL URL you want to work with."),
        required=True,)
    pm_timeout = schema.Int(
        title=_(u"PloneMeeting connection timeout"),
        description=_(u"Enter the timeout while connecting to PloneMeeting.  Do not set a too high timeout because it "
                      "will impact the load of the viewlet showing PM infos on an sent element if PM is not available."
                      "  Default is '10' seconds."),
        default=10,
        required=True,)
    pm_username = schema.TextLine(
        title=_("PloneMeeting username to use"),
        description=_(u"The user must be at least a 'MeetingManager'.  Nevertheless, items will be created regarding "
                      "the <i>User ids mappings</i> defined here under."),
        required=True,)
    pm_password = schema.Password(
        title=_("PloneMeeting password to use"),
        required=True,)
    viewlet_display_condition = schema.TextLine(
        title=_("Viewlet display condition"),
        description=_("Enter a TAL expression that will be evaluated to check if the viewlet displaying "
                      "informations about the created items in PloneMeeting should be displayed.  "
                      "If empty, the viewlet will only be displayed if an item is actually linked to it.  "
                      "The 'isLinked' variable representing this default behaviour is available in the TAL expression."),
        required=False,)
    field_mappings = schema.List(
        title=_("Field accessor mappings"),
        description=_("For every available data you can send, define in the mapping a TAL expression that will be "
                      "executed to obtain the correct value to send.  The 'meetingConfigId' and 'proposingGroupId' "
                      "variables are also available for the expression."),
        value_type=DictRow(title=_("Field mappings"),
                           schema=IFieldMappingsSchema,
                           required=False),
        required=False,)
    user_mappings = schema.List(
        title=_("User ids mappings"),
        description=_("By default, while sending an element to PloneMeeting, the user id of the logged in user "
                      "is used and a binding is made to the same user id in PloneMeeting.  "
                      "If the local user id does not exist in PloneMeeting, you can define here the user mappings "
                      "to use.  For example : 'jdoe' in 'Local user id' of the current application correspond to "
                      "'johndoe' in PloneMeeting."),
        value_type=DictRow(title=_("User mappings"),
                           schema=IUserMappingsSchema,
                           required=False),
        required=False,)
    generated_actions = schema.List(
        title=_("Generated actions"),
        description=_("Actions to send an item to PloneMeeting can be generated.  First enter a 'TAL condition' "
                      "evaluated to show the action then choose permission(s) the user must have to see the action.  "
                      "Finally, choose the meetingConfig the item will be sent to."),
        value_type=DictRow(title=_("Actions"),
                           schema=IGeneratedActionsSchema,
                           required=False),
        required=False,)


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
    fields['user_mappings'].widgetFactory = DataGridFieldFactory

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

    @memoize
    def settings(self):
        """ """
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IWS4PMClientSettings, check=False)
        return settings

    @memoize
    def _soap_connectToPloneMeeting(self):
        """
          Connect to distant PloneMeeting.
          Either return None or the connected client.
        """
        settings = self.settings()
        url = self.request.form.get('form.widgets.pm_url') or settings.pm_url
        username = self.request.form.get('form.widgets.pm_username') or settings.pm_username
        password = self.request.form.get('form.widgets.pm_password') or settings.pm_password
        timeout = self.request.form.get('form.widgets.pm_timeout') or settings.pm_timeout
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        t = HttpAuthenticated(username=username, password=password)
        try:
            client = Client(url, doctor=d, transport=t, timeout=int(timeout))
            # call a SOAP server test method to check that everything is fine with given parameters
            client.service.testConnection('')
        except Exception, e:
            # if we are really on the configuration panel, display relevant message
            if self.request.get('PATH_INFO', '').endswith('@@ws4pmclient-settings'):
                IStatusMessage(self.request).addStatusMessage(
                    _(CONFIG_UNABLE_TO_CONNECT_ERROR % (e.message or str(e.reason))), "error")
            return None
        return client

    def _soap_checkIsLinked(self, data):
        """Query the checkIsLinked SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.checkIsLinked(**data)

    @memoize
    def _soap_getConfigInfos(self, showCategories=False):
        """Query the getConfigInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            return client.service.getConfigInfos(showCategories=showCategories)

    @memoize
    def _soap_getUserInfos(self, showGroups=False, suffix=''):
        """Query the getConfigInfos SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            # get the inTheNameOf userid if it was not already set
            userId = self._getUserIdToUseInTheNameOfWith(mandatory=True)
            try:
                return client.service.getUserInfos(userId, showGroups, suffix)
            except Exception:
                return None

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

    def _soap_getItemTemplate(self, data):
        """Query the getItemTemplate SOAP server method."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            if not 'inTheNameOf' in data:
                data['inTheNameOf'] = self._getUserIdToUseInTheNameOfWith()
            try:
                return client.service.getItemTemplate(**data)
            except Exception, exc:
                    IStatusMessage(self.request).addStatusMessage(
                        _(u"An error occured while generating the document in PloneMeeting!  "
                          "The error message was : %s" % exc), "error")

    @memoize
    def _soap_getItemCreationAvailableData(self):
        """Query SOAP WSDL to obtain the list of available fields useable while creating an item."""
        client = self._soap_connectToPloneMeeting()
        if client is not None:
            # extract data from the CreationData ComplexType that is used to create an item
            namespace = str(client.wsdl.tns[1])
            res = ['proposingGroup']
            res += [str(data.name) for data in
                    client.factory.wsdl.build_schema().types['CreationData', namespace].rawchildren[0].rawchildren]
            return res

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
                IStatusMessage(self.request).addStatusMessage(_(CONFIG_CREATE_ITEM_PM_ERROR % exc), "error")

    def _getUserIdToUseInTheNameOfWith(self, mandatory=False):
        """
          Returns the userId that will actually create the item.
          Returns None if we found out that it is the defined settings.pm_username
          that will create the item : either it is the currently connected user,
          or there is an existing user_mapping between currently connected user
          and settings.pm_username user.
          If p_mandatory is True, returns mndatorily a userId.
        """
        member = self.context.portal_membership.getAuthenticatedMember()
        memberId = member.getId()
        # get username specified to connect to the SOAP distant site
        settings = self.settings()
        soapUsername = settings.pm_username and settings.pm_username.strip()
        # if current user is the user defined in the settings, return None
        if memberId == soapUsername:
            if mandatory:
                return soapUsername
            else:
                return None
        # check if a user_mapping exists
        for user_mapping in settings.user_mappings:
            localUserId, distantUserId = user_mapping['local_userid'], user_mapping['pm_userid']
            # if we found a mapping for the current user, check also
            # that the distantUserId the mapping is linking to, is not the soapUsername
            if memberId == localUserId.strip():
                if not soapUsername == distantUserId.strip():
                    return distantUserId.strip()
                else:
                    if mandatory:
                        return soapUsername
                    else:
                        return None
        return memberId

    def checkAlreadySentToPloneMeeting(self, context, meetingConfigIds=[]):
        """
          Check if the element has already been sent to PloneMeeting to avoid double sents
          If an item needs to be doubled in PloneMeeting, it is PloneMeeting's duty
          If p_meetingConfigIds is empty (), then it checks every available meetingConfigId it was sent to...
          The script will return :
          - 'None' if could not connect to PloneMeeting
          - True if the p_context is linked to an item of p_meetingConfigIds
          - False if p_context is not linked to an item of p_meetingConfigIds
          This script also wipe out every meetingConfigIds for wich the item does not exist anymore in PloneMeeting
        """
        annotations = IAnnotations(context)
        # for performance reason (avoid to connect to SOAP if no annotations)
        # if there are no relevant annotations, it means that the p_context
        # is not linked and we return False
        isLinked = False
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
                # if res is None, it means that it could not connect to PloneMeeting
                if res is None:
                    return None
                # we found at least one linked item
                elif res is True:
                    isLinked = True
                # could connect to PM but did not find a result
                elif res is False:
                    # either the item was deleted in PloneMeeting
                    # or it was never send, wipe out if it was deleted in PloneMeeting
                    if meetingConfigId in annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                        # do not use .remove directly on the annotations or it does not save
                        # correctly and when Zope restarts, the removed annotation is still there???
                        existingAnnotations = list(annotations[WS4PMCLIENT_ANNOTATION_KEY])
                        existingAnnotations.remove(meetingConfigId)
                        annotations[WS4PMCLIENT_ANNOTATION_KEY] = existingAnnotations
                    if not annotations[WS4PMCLIENT_ANNOTATION_KEY]:
                        # remove the entire annotation key if empty
                        del annotations[WS4PMCLIENT_ANNOTATION_KEY]
        return isLinked

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
        if res is None:
            return u''
        else:
            return res


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
            # get the pm_meeting_config_id_vocabulary so we will be able to displayValue
            factory = queryUtility(IVocabularyFactory, u'imio.pm.wsclient.pm_meeting_config_id_vocabulary')
            meetingConfigVocab = factory(portal)
            for actToGen in event.record.value:
                actionId = "%s%d" % (ACTION_SUFFIX, i)
                # get value from vocab
                action = Action(actionId,
                                title=translate(
                                    'Send to',
                                    domain='imio.pm.wsclient',
                                    mapping={'meetingConfigTitle':
                                             meetingConfigVocab.getTerm(actToGen['pm_meeting_config_id']).title},
                                    context=portal.REQUEST),
                                description='', i18n_domain='imio.pm.wsclient',
                                url_expr='string:${object_url}/@@send_to_plonemeeting_form?meetingConfigId=%s'
                                         % actToGen['pm_meeting_config_id'],
                                icon_expr='',
                                available_expr=actToGen['condition'],
                                permissions=(actToGen['permissions'], ),
                                visible=True)
                object_buttons._setObject(actionId, action)
                i = i + 1
